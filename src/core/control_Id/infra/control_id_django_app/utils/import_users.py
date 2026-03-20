from src.core.user.infra.user_django_app.models import User
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup as Group
from src.core.control_Id.infra.control_id_django_app.models import UserGroup
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers
from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
import pandas as pd
import re
import tempfile
from django.core.files.uploadedfile import InMemoryUploadedFile
import os


class FileUploadSerializer(serializers.Serializer):
    """Serializer para upload de arquivo Excel"""

    file = serializers.FileField(
        help_text="Arquivo Excel (.xlsx) com usuários para importar. Formato: abas como '1INFO1(2025)', '1AGRO1(2025)', ou '1QUIMI (2025)' com colunas ORDEM, MATRICULA, NOME_COMPLETO"
    )


class ImportUsersView(ControlIDSyncMixin, APIView):
    """
    View to import users (students) from an Excel file with multiple sheets (grupos).
    Each sheet represents a grupo (e.g., '1INFO1(2025)', '1AGRO1(2025)', '1QUIMI (2025)'), and creates/updates users
    associated with the parsed grupo via M2M relation (UserGroup).
    Also creates users in all active catracas automatically.
    """

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileUploadSerializer

    def _build_user_payload(self, user):
        payload = {
            "id": user.id,
            "name": user.name,
            "registration": user.registration,
        }
        if getattr(user, "user_type_id", None) is not None:
            payload["user_type_id"] = user.user_type_id
        return payload

    def _sync_user_in_device(self, user, device):
        self.set_device(device)

        create_response = self.create_or_update_objects(
            "users",
            [self._build_user_payload(user)],
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            update_response = self.update_objects(
                "users",
                {
                    "name": user.name,
                    "registration": user.registration or "",
                    **(
                        {"user_type_id": user.user_type_id}
                        if getattr(user, "user_type_id", None) is not None
                        else {}
                    ),
                },
                {"users": {"id": user.id}},
            )
            if update_response.status_code != status.HTTP_200_OK:
                return (
                    False,
                    f"Erro ao sincronizar usuário na catraca {device.name}: "
                    f"{getattr(update_response, 'data', update_response.__dict__)}",
                )

        if hasattr(user, "pin") and user.pin:
            pin_response = self.update_objects(
                "pins",
                {"value": user.pin},
                {"pins": {"user_id": user.id}},
            )
            if pin_response.status_code != status.HTTP_200_OK:
                pin_response = self.create_objects(
                    "pins",
                    [{"user_id": user.id, "value": user.pin}],
                )
                if pin_response.status_code != status.HTTP_201_CREATED:
                    return (
                        False,
                        f"Erro ao sincronizar PIN na catraca {device.name}: "
                        f"{getattr(pin_response, 'data', pin_response.__dict__)}",
                    )

        return True, None

    def sync_user_in_catraca(self, user):
        """
        Sincroniza o usuário em todas as catracas ativas.
        Tenta create primeiro; se falhar, faz update (usuário já existe na catraca).
        """
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            for device in devices:
                success, error_message = self._sync_user_in_device(user, device)
                if not success:
                    return False, error_message

            return True, "Usuário sincronizado com sucesso em todas as catracas"
        except Exception as e:
            return False, f"Erro ao sincronizar usuário na catraca: {str(e)}"

    def get(self, request, *args, **kwargs):
        """
        Retorna informações sobre como usar a API de importação.
        """
        return Response(
            {
                "message": "Upload de arquivo Excel para importação de usuários",
                "instructions": {
                    "method": "POST",
                    "content_type": "multipart/form-data",
                    "field_name": "file",
                    "file_format": ".xlsx",
                    "sheet_format": "1INFO1(2025), 1AGRO1(2025), 1QUIMI (2025), etc.",
                    "required_columns": ["ORDEM", "Matrícula", "Nome"],
                },
                "example": {
                    "curl": "curl -X POST -F 'file=@usuarios.xlsx' http://localhost:8000/api/control_id/import-users/"
                },
            }
        )

    def create_group_in_catraca(self, group):
        """
        Cria o grupo em todas as catracas ativas.
        Garante broadcast para todos os devices limpando self._device antes.
        """
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            # Garante que vai para todos os devices, não apenas o último setado
            self._device = None
            print(f"[SYNC] Criando grupo na catraca: id={group.id} name={group.name}")

            response = self.create_objects(
                "groups", [{"id": group.id, "name": group.name}]
            )
            print(f"[SYNC] Resposta grupo: status={response.status_code} data={getattr(response, 'data', None)}")
            if response.status_code != status.HTTP_201_CREATED:
                return (
                    False,
                    f"Erro ao criar grupo na catraca: {getattr(response, 'data', response.__dict__)}",
                )

            return True, "Grupo criado com sucesso em todas as catracas"

        except Exception as e:
            print(f"[SYNC] EXCEPTION grupo: {str(e)}")
            return False, f"Erro ao criar grupo na catraca: {str(e)}"

    def create_group_local_then_remote(self, group_name: str):
        """
        Cria primeiro o grupo no Django e replica para as catracas usando o ID local.
        Retorna (instance, error_message)
        """
        try:
            sp = transaction.savepoint()
            try:
                instance = Group.objects.create(name=group_name)
                success, error_message = self.create_group_in_catraca(instance)
                if not success:
                    transaction.savepoint_rollback(sp)
                    return None, error_message
                transaction.savepoint_commit(sp)
                return instance, None
            except Exception as e:
                transaction.savepoint_rollback(sp)
                return None, str(e)
        except Exception as e:
            return None, str(e)

    def post(self, request, *args, **kwargs):
        tmp_path = None
        try:
            file: InMemoryUploadedFile = request.FILES.get("file")
            if not file:
                return Response(
                    {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
                )

            if not re.match(r".*\.xlsx$", file.name):
                return Response(
                    {"error": "Invalid file format. Please upload an .xlsx file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
                tmp.flush()

            excel_file = pd.ExcelFile(tmp_path)
            sheet_names = excel_file.sheet_names
            excel_file.close()

            if not sheet_names:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                return Response(
                    {"error": "No sheets found in the Excel file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            created_users = 0
            updated_users = 0
            created_groups = 0
            updated_groups = 0
            created_relations = 0
            catraca_errors = []
            errors = []

            for sheet_name in sheet_names:
                sheet_name = str(sheet_name).strip()
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)

                if len(df.columns) != 3:
                    errors.append(
                        f"Sheet '{sheet_name}': Expected exactly 3 columns (ORDEM, Matrícula, Nome)"
                    )
                    continue
                df.columns = ["ORDEM", "Matrícula", "Nome"]

                if not {"Matrícula", "Nome"}.issubset(df.columns) or df.empty:
                    errors.append(
                        f"Sheet '{sheet_name}': Missing required columns or empty sheet"
                    )
                    continue

                match_full = re.match(r"(\d+)([A-Z]+)(\d+)\s*\((\d+)\)", sheet_name)
                if not match_full:
                    errors.append(
                        f"Sheet '{sheet_name}': Invalid sheet name format. Expected: '1INFO1(2025)', '1AGRO1(2025)', etc."
                    )
                    continue

                nivel = int(match_full.group(1))
                curso = match_full.group(2)
                secao = int(match_full.group(3))
                nome_grupo = f"{nivel}{curso}{secao}"

                with transaction.atomic():
                    # ── 1. Grupo ─────────────────────────────────────────────────
                    # Garante que o grupo existe no Django e na catraca antes de
                    # qualquer operação de usuário — evita FK quebrada nas relações.
                    grupo = Group.objects.filter(name=nome_grupo).first()
                    if not grupo:
                        # _device = None garante broadcast para todos os devices
                        self._device = None
                        grupo, err = self.create_group_local_then_remote(nome_grupo)
                        if err:
                            catraca_errors.append(f"Grupo {nome_grupo}: {err}")
                            continue
                        created_groups += 1
                    else:
                        updated_groups += 1

                    # ── 2. Pré-processa linhas válidas ────────────────────────────
                    rows_valid = []
                    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
                        if pd.isna(row["Matrícula"]) or pd.isna(row["Nome"]):
                            errors.append(
                                f"Sheet '{sheet_name}', row {row_number}: Missing Matrícula or Nome"
                            )
                            continue
                        rows_valid.append({
                            "name": str(row["Nome"]).strip(),
                            "registration": str(row["Matrícula"]).strip(),
                            "email": f"{str(row['Matrícula']).strip()}@escola.edu",
                        })

                    if not rows_valid:
                        continue

                    # ── 3. Resolve users no Django (create ou update local) ────────
                    users_to_create_remote = []  # novos: batch create na catraca
                    users_to_update_remote = []  # existentes: sync create-or-update por device

                    for row in rows_valid:
                        user = (
                            User.objects.filter(registration=row["registration"]).first()
                            or User.objects.filter(email=row["email"]).first()
                        )
                        if not user:
                            user = User.objects.create(
                                name=row["name"],
                                registration=row["registration"],
                                email=row["email"],
                                is_active=True,
                            )
                            users_to_create_remote.append(user)
                            created_users += 1
                        else:
                            if (
                                user.name != row["name"]
                                or user.registration != row["registration"]
                                or not user.is_active
                            ):
                                user.name = row["name"]
                                user.registration = row["registration"]
                                user.is_active = True
                                user.save(update_fields=["name", "registration", "is_active"])
                            users_to_update_remote.append(user)
                            updated_users += 1

                    # ── 4. Batch create na catraca (todos os novos de uma vez) ─────
                    # synced_users controla quem foi confirmado na catraca.
                    # Relações só são criadas para estes — evita FK quebrada.
                    synced_users = []

                    if users_to_create_remote:
                        self._device = None  # broadcast para todos os devices
                        batch_payload = [self._build_user_payload(u) for u in users_to_create_remote]
                        print(f"[SYNC] Batch create users: {[p['id'] for p in batch_payload]}")
                        response = self.create_objects("users", batch_payload)
                        print(f"[SYNC] Resposta batch users: status={response.status_code} data={getattr(response, 'data', None)}")
                        if response.status_code != status.HTTP_201_CREATED:
                            catraca_errors.append(
                                f"Sheet '{sheet_name}': Erro ao criar batch de "
                                f"{len(batch_payload)} usuários: "
                                f"{getattr(response, 'data', str(response))}"
                            )
                            # Usuários não confirmados ficam fora de synced_users
                        else:
                            synced_users.extend(users_to_create_remote)

                    # ── 5. Sync usuários existentes (create-or-update por device) ──
                    # sync_user_in_catraca tenta create primeiro; se o usuário já
                    # existir na catraca, faz update — cobre casos de reimportação
                    # após falha parcial anterior.
                    for user in users_to_update_remote:
                        print(f"[SYNC] Sync user existente: id={user.id} name={user.name} registration={user.registration}")
                        self._device = None  # reseta para iterar todos os devices
                        success, err = self.sync_user_in_catraca(user)
                        print(f"[SYNC] Resultado sync user id={user.id}: success={success} err={err}")
                        if not success:
                            catraca_errors.append(
                                f"Usuário {user.name} ({user.registration}): {err}"
                            )
                            # Não entra em synced_users — FK das relações ficaria quebrada
                        else:
                            synced_users.append(user)

                    # ── 6. Relações UserGroup apenas para usuários confirmados ──────
                    if synced_users:
                        new_relation_pairs = []
                        for user in synced_users:
                            _, created = UserGroup.objects.get_or_create(
                                user=user, group=grupo
                            )
                            if created:
                                new_relation_pairs.append(user)
                                created_relations += 1

                        if new_relation_pairs:
                            self._device = None  # broadcast para todos os devices
                            relations_payload = [
                                {"user_id": u.id, "group_id": grupo.id}
                                for u in new_relation_pairs
                            ]
                            print(f"[SYNC] Batch create user_groups: {relations_payload}")
                            response = self.create_or_update_objects("user_groups", relations_payload)
                            print(f"[SYNC] Resposta user_groups: status={response.status_code} data={getattr(response, 'data', None)}")
                            if response.status_code != status.HTTP_201_CREATED:
                                catraca_errors.append(
                                    f"Sheet '{sheet_name}': Erro ao criar batch de relações: "
                                    f"{getattr(response, 'data', str(response))}"
                                )

            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            response_data = {
                "success": True,
                "message": (
                    f"Import completed. "
                    f"Groups: Created {created_groups}, Updated {updated_groups}. "
                    f"Users: Created {created_users}, Updated {updated_users}. "
                    f"Relations: Created {created_relations}"
                ),
                "sheets_processed": len(sheet_names),
                "errors": errors or None,
                "catraca_errors": catraca_errors or None,
            }

            status_code = (
                status.HTTP_200_OK
                if not (errors or catraca_errors)
                else status.HTTP_207_MULTI_STATUS
            )
            return Response(response_data, status=status_code)

        except Exception as e:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            return Response(
                {"error": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )