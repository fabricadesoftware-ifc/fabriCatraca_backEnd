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

        create_response = self.create_objects(
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

    def create_user_in_catraca(self, user):
        """
        Cria o usuário em todas as catracas ativas usando a mesma lógica do UserViewSet.
        """
        return self.sync_user_in_catraca(user)

    def create_group_in_catraca(self, group):
        """
        Cria o grupo em todas as catracas ativas.
        """
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            response = self.create_objects(
                "groups", [{"id": group.id, "name": group.name}]
            )

            if response.status_code != status.HTTP_201_CREATED:
                return (
                    False,
                    f"Erro ao criar grupo na catraca: {getattr(response, 'data', response.__dict__)}",
                )

            return True, "Grupo criado com sucesso em todas as catracas"

        except Exception as e:
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

    def create_user_local_then_remote(self, name: str, registration: str, email: str):
        """
        Cria primeiro o usuário no Django e replica para as catracas usando o ID local.
        Retorna (instance, error_message)
        """
        try:
            sp = transaction.savepoint()
            try:
                instance = User.objects.create(
                    name=name,
                    registration=registration,
                    email=email,
                    is_active=True,
                )
                success, error_message = self.create_user_in_catraca(instance)
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

    def create_user_group_relation_in_catraca(self, user, group):
        """
        Cria a relação usuário-grupo em todas as catracas ativas.
        """
        try:
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            for device in devices:
                self.set_device(device)

                response = self.create_objects(
                    "user_groups", [{"user_id": user.id, "group_id": group.id}]
                )

                if response.status_code != status.HTTP_201_CREATED:
                    return (
                        False,
                        f"Erro ao criar relação usuário-grupo na catraca {device.name}: {response.data}",
                    )

            return True, "Relação usuário-grupo criada com sucesso em todas as catracas"

        except Exception as e:
            return False, f"Erro ao criar relação usuário-grupo na catraca: {str(e)}"

    def post(self, request, *args, **kwargs):
        tmp_path = None
        try:
            file: InMemoryUploadedFile = request.FILES.get("file")
            if not file:
                return Response(
                    {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Verifica se o arquivo é um Excel válido
            if not re.match(r".*\.xlsx$", file.name):
                return Response(
                    {"error": "Invalid file format. Please upload an .xlsx file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Salva o arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
                tmp.flush()

            # Lê o arquivo Excel e obtém nomes das abas
            excel_file = pd.ExcelFile(tmp_path)
            sheet_names = excel_file.sheet_names
            excel_file.close()
            print(sheet_names)

            if not sheet_names:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                return Response(
                    {"error": "No sheets found in the Excel file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Estatísticas gerais
            created_users = 0
            updated_users = 0
            created_groups = 0
            updated_groups = 0
            created_relations = 0
            catraca_errors = []
            errors = []

            for sheet_name in sheet_names:
                sheet_name = str(sheet_name).strip()
                # Carrega os dados da aba
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)

                # Padroniza colunas
                if len(df.columns) != 3:
                    errors.append(
                        f"Sheet '{sheet_name}': Expected exactly 3 columns (ORDEM, Matrícula, Nome)"
                    )
                    continue
                df.columns = ["ORDEM", "Matrícula", "Nome"]

                # Verifica colunas requeridas
                required_columns = {"Matrícula", "Nome"}
                if not required_columns.issubset(df.columns):
                    errors.append(
                        f"Sheet '{sheet_name}': Missing required columns: {required_columns - set(df.columns)}"
                    )
                    continue

                # Verifica se a aba tem dados
                if df.empty:
                    errors.append(f"Sheet '{sheet_name}': No data found in the sheet")
                    continue

                # Parseia o nome da aba
                nome_grupo = None
                print(f"[DEBUG] Processando aba: '{sheet_name}'")

                match_full = re.match(
                    r"(\d+)([A-Z]+)(\d+)\s*\((\d+)\)", sheet_name
                )  # Ex.: 1INFO1(2025), 1AGRO2(2025), 1QUIMI1 (2025)

                if match_full:
                    nivel = int(match_full.group(1))  # Ex.: 1
                    curso = match_full.group(2)  # Ex.: INFO, AGRO QUIMI
                    secao = int(match_full.group(3))  # Ex.: 1
                    nome_grupo = f"{nivel}{curso}{secao}"  # Ex.: 1INFO1
                    print(
                        f"[DEBUG] Match completo - Nível: {nivel}, Curso: {curso}, Seção: {secao}, Nome final: {nome_grupo}"
                    )
                else:
                    print(f"[DEBUG] Nenhum match encontrado para a aba: '{sheet_name}'")
                    errors.append(
                        f"Sheet '{sheet_name}': Invalid sheet name format. Expected: '1INFO1(2025)', '1AGRO1(2025)', or '1QUIMI (2025)'"
                    )
                    continue

                # Cria ou reaproveita o grupo localmente e replica para as catracas com o ID do Django
                with transaction.atomic():
                    sp_group = transaction.savepoint()
                    try:
                        print(
                            f"[DEBUG] Verificando se grupo '{nome_grupo}' já existe localmente"
                        )
                        grupo = Group.objects.filter(name=nome_grupo).first()

                        if not grupo:
                            print(
                                f"[DEBUG] Grupo '{nome_grupo}' não existe localmente, tentando criar na catraca"
                            )
                            # Verifica se já existe na catraca
                            try:
                                all_groups = self.load_objects(
                                    "groups", fields=["id", "name"]
                                )
                                print(
                                    f"[DEBUG] Grupos existentes na catraca: {[{'id': g.get('id'), 'name': g.get('name')} for g in all_groups]}"
                                )
                            except Exception as e:
                                print(
                                    f"[DEBUG] Erro ao listar grupos da catraca: {str(e)}"
                                )

                            grupo, err = self.create_group_local_then_remote(nome_grupo)
                            if err:
                                print(
                                    f"[DEBUG] Erro ao criar grupo '{nome_grupo}': {err}"
                                )
                                transaction.savepoint_rollback(sp_group)
                                catraca_errors.append(f"Grupo {nome_grupo}: {err}")
                                continue
                            print(
                                f"[DEBUG] Grupo '{nome_grupo}' criado com sucesso (ID: {getattr(grupo, 'id', 'N/A')})"
                            )
                            created_groups += 1
                        else:
                            print(
                                f"[DEBUG] Grupo '{nome_grupo}' já existe localmente (ID: {getattr(grupo, 'id', 'N/A')})"
                            )
                            updated_groups += 1
                        transaction.savepoint_commit(sp_group)
                    except Exception as e:
                        print(
                            f"[DEBUG] Erro não tratado ao processar grupo '{nome_grupo}': {str(e)}"
                        )
                        transaction.savepoint_rollback(sp_group)
                        catraca_errors.append(f"Grupo {nome_grupo}: {str(e)}")
                        continue

                    # Para cada aluno, cria/atualiza User e cria a relação UserGroup
                    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
                        sp_user = transaction.savepoint()
                        if pd.isna(row["Matrícula"]) or pd.isna(row["Nome"]):
                            errors.append(
                                f"Sheet '{sheet_name}', row {row_number}: Missing MATRICULA or Nome"
                            )
                            transaction.savepoint_rollback(sp_user)
                            continue

                        email = f"{row['Matrícula']}@escola.edu"

                        name_user = str(row["Nome"]).strip()
                        registration = str(row["Matrícula"]).strip()

                        try:
                            # Usa registration como chave preferencial para evitar duplicidade por email
                            user = (
                                User.objects.filter(registration=registration).first()
                                or User.objects.filter(email=email).first()
                            )
                            if not user:
                                user, err = self.create_user_local_then_remote(
                                    name_user, registration, email
                                )
                                if err:
                                    transaction.savepoint_rollback(sp_user)
                                    catraca_errors.append(
                                        f"Usuário {name_user} ({registration}): {err}"
                                    )
                                    continue
                                created_users += 1
                            else:
                                # Atualiza dados básicos no Django (não altera ID)
                                if (
                                    user.name != name_user
                                    or user.registration != registration
                                    or not user.is_active
                                ):
                                    user.name = name_user
                                    user.registration = registration
                                    user.is_active = True
                                    user.save(
                                        update_fields=[
                                            "name",
                                            "registration",
                                            "is_active",
                                        ]
                                    )

                                success, err = self.sync_user_in_catraca(user)
                                if not success:
                                    transaction.savepoint_rollback(sp_user)
                                    catraca_errors.append(
                                        f"Usuário {name_user} ({registration}): {err}"
                                    )
                                    continue

                                updated_users += 1
                        except Exception as e:
                            transaction.savepoint_rollback(sp_user)
                            catraca_errors.append(
                                f"Usuário {name_user} ({registration}): {str(e)}"
                            )
                            continue

                        try:
                            relacao_existente, created = (
                                UserGroup.objects.get_or_create(user=user, group=grupo)
                            )
                            if created:
                                created_relations += 1
                                success, message = (
                                    self.create_user_group_relation_in_catraca(
                                        user, grupo
                                    )
                                )
                                if not success:
                                    raise Exception(message)
                            transaction.savepoint_commit(sp_user)
                        except Exception as e:
                            transaction.savepoint_rollback(sp_user)
                            catraca_errors.append(
                                f"Relação {name_user}-{getattr(grupo, 'name', nome_grupo)}: {str(e)}"
                            )
                            continue

            # Limpa o arquivo temp
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            response_data = {
                "success": True,
                "message": f"Import completed. Groups: Created {created_groups}, Updated {updated_groups}. Users: Created {created_users}, Updated {updated_users}. Relations: Created {created_relations}",
                "sheets_processed": len(sheet_names),
                "errors": errors if errors else None,
                "catraca_errors": catraca_errors if catraca_errors else None,
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
