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
import logging

logger = logging.getLogger(__name__)


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
    Also creates users in all active catracas automatically via batch upsert.
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

    def get(self, request, *args, **kwargs):
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
        Cria ou atualiza o grupo em todas as catracas ativas via upsert.
        """
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            self._device = None
            logger.info(f"[GRUPO] Sincronizando grupo id={group.id} name='{group.name}' em {len(devices)} catraca(s)")

            response = self.create_or_update_objects_in_all_devices(
                "groups", [{"id": group.id, "name": group.name}]
            )

            if response.status_code != status.HTTP_200_OK:
                error_detail = getattr(response, "data", str(response))
                logger.error(f"[GRUPO] Falha ao sincronizar grupo id={group.id} name='{group.name}': {error_detail}")
                return False, f"Erro ao sincronizar grupo na catraca: {error_detail}"

            logger.info(f"[GRUPO] Grupo id={group.id} name='{group.name}' sincronizado com sucesso")
            return True, None

        except Exception as e:
            logger.exception(f"[GRUPO] Exceção ao sincronizar grupo id={group.id} name='{group.name}': {str(e)}")
            return False, f"Erro ao sincronizar grupo na catraca: {str(e)}"

    def create_group_local_then_remote(self, group_name: str):
        """
        Cria primeiro o grupo no Django e replica para as catracas usando o ID local.
        Retorna (instance, error_message)
        """
        try:
            sp = transaction.savepoint()
            try:
                instance = Group.objects.create(name=group_name)
                logger.info(f"[GRUPO] Grupo '{group_name}' criado localmente com id={instance.id}")
                success, error_message = self.create_group_in_catraca(instance)
                if not success:
                    transaction.savepoint_rollback(sp)
                    logger.error(f"[GRUPO] Rollback do grupo '{group_name}' após falha na catraca: {error_message}")
                    return None, error_message
                transaction.savepoint_commit(sp)
                return instance, None
            except Exception as e:
                transaction.savepoint_rollback(sp)
                logger.exception(f"[GRUPO] Exceção ao criar grupo '{group_name}' localmente: {str(e)}")
                return None, str(e)
        except Exception as e:
            logger.exception(f"[GRUPO] Exceção externa ao criar grupo '{group_name}': {str(e)}")
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

            logger.info(f"[IMPORT] Arquivo recebido com {len(sheet_names)} aba(s): {sheet_names}")

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
                logger.info(f"[IMPORT] ── Iniciando aba '{sheet_name}' ──")

                df = pd.read_excel(tmp_path, sheet_name=sheet_name)

                if len(df.columns) != 3:
                    msg = f"Sheet '{sheet_name}': Expected exactly 3 columns (ORDEM, Matrícula, Nome)"
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue
                df.columns = ["ORDEM", "Matrícula", "Nome"]

                if not {"Matrícula", "Nome"}.issubset(df.columns) or df.empty:
                    msg = f"Sheet '{sheet_name}': Missing required columns or empty sheet"
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue

                match_full = re.match(r"(\d+)([A-Z]+)(\d+)\s*\((\d+)\)", sheet_name)
                if not match_full:
                    msg = f"Sheet '{sheet_name}': Invalid sheet name format. Expected: '1INFO1(2025)', '1AGRO1(2025)', etc."
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue

                nivel = int(match_full.group(1))
                curso = match_full.group(2)
                secao = int(match_full.group(3))
                nome_grupo = f"{nivel}{curso}{secao}"

                with transaction.atomic():
                    # ── 1. Grupo ──────────────────────────────────────────────────
                    # Garante que o grupo existe no Django e na catraca antes de
                    # qualquer operação de usuário — evita FK quebrada nas relações.
                    grupo = Group.objects.filter(name=nome_grupo).first()
                    if not grupo:
                        self._device = None
                        logger.info(f"[GRUPO] Grupo '{nome_grupo}' não existe localmente — criando")
                        grupo, err = self.create_group_local_then_remote(nome_grupo)
                        if err:
                            logger.error(f"[GRUPO] Falha ao criar grupo '{nome_grupo}': {err}")
                            catraca_errors.append(f"Grupo {nome_grupo}: {err}")
                            continue
                        created_groups += 1
                    else:
                        # Mesmo existindo no Django, garante que está em todos os devices
                        self._device = None
                        logger.info(f"[GRUPO] Grupo '{nome_grupo}' existe localmente — garantindo sync em todos os devices")
                        success, err = self.create_group_in_catraca(grupo)
                        if err:
                            logger.error(f"[GRUPO] Falha ao sincronizar grupo existente '{nome_grupo}': {err}")
                            catraca_errors.append(f"Grupo {nome_grupo}: {err}")
                            continue
                        updated_groups += 1

                    # ── 2. Pré-processa linhas válidas ─────────────────────────────
                    rows_valid = []
                    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
                        if pd.isna(row["Matrícula"]) or pd.isna(row["Nome"]):
                            msg = f"Sheet '{sheet_name}', row {row_number}: Missing Matrícula or Nome"
                            logger.warning(f"[IMPORT] {msg}")
                            errors.append(msg)
                            continue
                        rows_valid.append({
                            "name": str(row["Nome"]).strip(),
                            "registration": str(row["Matrícula"]).strip(),
                            "email": f"{str(row['Matrícula']).strip()}@escola.edu",
                        })

                    if not rows_valid:
                        logger.warning(f"[IMPORT] Aba '{sheet_name}' sem linhas válidas após filtragem — pulando")
                        continue

                    logger.info(f"[IMPORT] Aba '{sheet_name}': {len(rows_valid)} aluno(s) válido(s)")

                    # ── 3. Resolve users no Django (create ou update local) ─────────
                    users_to_create_remote = []
                    users_to_update_remote = []

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
                            logger.info(f"[USER] Novo usuário criado localmente: id={user.id} name='{user.name}' registration={user.registration}")
                            users_to_create_remote.append(user)
                            created_users += 1
                        else:
                            if (
                                user.name != row["name"]
                                or user.registration != row["registration"]
                                or not user.is_active
                            ):
                                logger.info(f"[USER] Atualizando localmente: id={user.id} '{user.name}' → '{row['name']}'")
                                user.name = row["name"]
                                user.registration = row["registration"]
                                user.is_active = True
                                user.save(update_fields=["name", "registration", "is_active"])
                            else:
                                logger.info(f"[USER] Sem alterações locais: id={user.id} name='{user.name}'")
                            users_to_update_remote.append(user)
                            updated_users += 1

                    logger.info(
                        f"[USER] Aba '{sheet_name}': {len(users_to_create_remote)} novo(s), "
                        f"{len(users_to_update_remote)} existente(s)"
                    )

                    # ── 4+5. Batch upsert de TODOS os usuários na catraca ──────────
                    # Novos e existentes vão juntos num único request por device.
                    # create_or_update_objects_in_all_devices usa create_or_modify_objects.fcgi
                    # que resolve o upsert nativamente — sem UNIQUE constraint error.
                    # synced_users controla quem foi confirmado na catraca:
                    # relações só são criadas para estes, evitando FK quebrada.
                    synced_users = []
                    all_users = users_to_create_remote + users_to_update_remote

                    if all_users:
                        self._device = None
                        batch_payload = [self._build_user_payload(u) for u in all_users]
                        logger.info(
                            f"[CATRACA] Enviando batch upsert de {len(batch_payload)} usuário(s) "
                            f"ids={[p['id'] for p in batch_payload]}"
                        )
                        response = self.create_or_update_objects_in_all_devices("users", batch_payload)
                        logger.info(
                            f"[CATRACA] Resposta batch users: status={response.status_code} "
                            f"data={getattr(response, 'data', None)}"
                        )
                        if response.status_code != status.HTTP_200_OK:
                            error_detail = getattr(response, "data", str(response))
                            logger.error(
                                f"[CATRACA] Falha no batch upsert de usuários da aba '{sheet_name}': {error_detail}"
                            )
                            catraca_errors.append(
                                f"Sheet '{sheet_name}': Erro ao sincronizar batch de "
                                f"{len(batch_payload)} usuário(s): {error_detail}"
                            )
                            # Nenhum usuário confirmado — relações não serão criadas
                        else:
                            synced_users.extend(all_users)
                            logger.info(
                                f"[CATRACA] Batch upsert confirmado: {len(synced_users)} usuário(s) sincronizado(s)"
                            )

                    # ── 6. Relações UserGroup apenas para usuários confirmados ───────
                    if synced_users:
                        new_relation_pairs = []
                        for user in synced_users:
                            _, created = UserGroup.objects.get_or_create(
                                user=user, group=grupo
                            )
                            if created:
                                new_relation_pairs.append(user)
                                created_relations += 1

                        logger.info(
                            f"[RELACAO] {len(new_relation_pairs)} nova(s) relação(ões) para criar "
                            f"(grupo id={grupo.id} name='{grupo.name}')"
                        )

                        if new_relation_pairs:
                            self._device = None
                            relations_payload = [
                                {"user_id": u.id, "group_id": grupo.id}
                                for u in new_relation_pairs
                            ]
                            logger.info(
                                f"[CATRACA] Enviando batch upsert de {len(relations_payload)} relação(ões): "
                                f"{relations_payload}"
                            )
                            response = self.create_or_update_objects_in_all_devices(
                                "user_groups", relations_payload
                            )
                            logger.info(
                                f"[CATRACA] Resposta batch user_groups: status={response.status_code} "
                                f"data={getattr(response, 'data', None)}"
                            )
                            if response.status_code != status.HTTP_200_OK:
                                error_detail = getattr(response, "data", str(response))
                                logger.error(
                                    f"[CATRACA] Falha no batch de relações da aba '{sheet_name}': {error_detail}"
                                )
                                catraca_errors.append(
                                    f"Sheet '{sheet_name}': Erro ao criar batch de relações: {error_detail}"
                                )
                    else:
                        logger.warning(
                            f"[RELACAO] Nenhum usuário confirmado na catraca para aba '{sheet_name}' — relações ignoradas"
                        )

                logger.info(f"[IMPORT] ── Aba '{sheet_name}' concluída ──")

            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            logger.info(
                f"[IMPORT] Importação finalizada — "
                f"Groups: created={created_groups} updated={updated_groups} | "
                f"Users: created={created_users} updated={updated_users} | "
                f"Relations: created={created_relations} | "
                f"errors={len(errors)} catraca_errors={len(catraca_errors)}"
            )

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
            logger.exception(f"[IMPORT] Exceção não tratada ao processar arquivo: {str(e)}")
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            return Response(
                {"error": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )