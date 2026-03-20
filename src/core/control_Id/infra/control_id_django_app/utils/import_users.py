import logging
import os
import re
import tempfile

import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup as Group
from src.core.control_Id.infra.control_id_django_app.models import UserGroup
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)


SHEET_NAME_PATTERN = re.compile(r"(\d+)([A-Za-z]+)(\d+)\s*\((\d+)\)")
REQUIRED_COLUMNS = ["ORDEM", "Matrícula", "Nome"]
EXCEL_EXTENSION_PATTERN = re.compile(r".*\.xlsx$")



class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text=(
            "Arquivo Excel (.xlsx) com usuários para importar. "
            "Abas no formato '1INFO1(2025)', colunas: ORDEM, Matrícula, Nome"
        )
    )



class ImportUsersView(ControlIDSyncMixin, APIView):
    """
    Importa alunos de um arquivo Excel com múltiplas abas.

    Cada aba representa uma turma (ex: '1INFO1(2025)') e gera:
      - Um Group no Django e em todas as catracas ativas
      - Users vinculados à turma via UserGroup

    Usa batch upsert nativo da catraca (create_or_modify_objects.fcgi)
    para criar e atualizar em um único request por device.
    """

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileUploadSerializer

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _build_user_payload(self, user: User) -> dict:
        payload = {
            "id": user.id,
            "name": user.name,
            "registration": user.registration,
        }
        if getattr(user, "user_type_id", None) is not None:
            payload["user_type_id"] = user.user_type_id
        return payload

    def _parse_sheet_name(self, sheet_name: str) -> str | None:
        """
        Extrai o nome do grupo a partir do nome da aba.
        Ex: '1INFO1(2025)' → '1INFO1', '3quimi2(2025)' → '3QUIMI2'
        Retorna None se o formato não for reconhecido.
        """
        match = SHEET_NAME_PATTERN.match(sheet_name)
        if not match:
            return None
        nivel = match.group(1)
        curso = match.group(2).upper()
        secao = match.group(3)
        return f"{nivel}{curso}{secao}"


    def _sync_group(self, group: Group) -> tuple[bool, str | None]:
        """
        Upsert do grupo em todas as catracas ativas.
        Garante que o grupo existe em todos os devices antes de criar relações.
        """
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            self._device = None
            logger.info(f"[GRUPO] Sincronizando id={group.id} name='{group.name}' → {len(devices)} device(s)")

            response = self.create_or_update_objects_in_all_devices(
                "groups", [{"id": group.id, "name": group.name}]
            )

            if response.status_code != status.HTTP_200_OK:
                error_detail = getattr(response, "data", str(response))
                logger.error(f"[GRUPO] Falha id={group.id} name='{group.name}': {error_detail}")
                return False, f"Erro ao sincronizar grupo na catraca: {error_detail}"

            logger.info(f"[GRUPO] OK id={group.id} name='{group.name}'")
            return True, None

        except Exception as e:
            logger.exception(f"[GRUPO] Exceção id={group.id} name='{group.name}': {e}")
            return False, str(e)

    def _ensure_group(self, nome_grupo: str) -> tuple[Group | None, str | None]:
        """
        Garante que o grupo existe no Django e em todas as catracas.
        Cria localmente se não existir, depois faz upsert na catraca.
        Retorna (grupo, erro).
        """
        self._device = None
        grupo = Group.objects.filter(name=nome_grupo).first()

        if not grupo:
            logger.info(f"[GRUPO] '{nome_grupo}' não existe — criando localmente")
            sp = transaction.savepoint()
            try:
                grupo = Group.objects.create(name=nome_grupo)
                logger.info(f"[GRUPO] Criado localmente: id={grupo.id}")
            except Exception as e:
                transaction.savepoint_rollback(sp)
                logger.exception(f"[GRUPO] Falha ao criar '{nome_grupo}' localmente: {e}")
                return None, str(e)
        else:
            logger.info(f"[GRUPO] '{nome_grupo}' já existe localmente (id={grupo.id})")
            sp = transaction.savepoint()

        success, err = self._sync_group(grupo)
        if not success:
            transaction.savepoint_rollback(sp)
            logger.error(f"[GRUPO] Rollback de '{nome_grupo}' após falha na catraca: {err}")
            return None, err

        transaction.savepoint_commit(sp)
        return grupo, None

    def _sync_users_batch(self, users: list[User], sheet_name: str) -> list[User]:
        """
        Upsert em batch de todos os usuários em todas as catracas.
        Retorna apenas os usuários confirmados na catraca.
        """
        if not users:
            return []

        self._device = None
        batch_payload = [self._build_user_payload(u) for u in users]

        logger.info(
            f"[USERS] Batch upsert de {len(batch_payload)} usuário(s) "
            f"ids={[p['id'] for p in batch_payload]}"
        )

        response = self.create_or_update_objects_in_all_devices("users", batch_payload)

        logger.info(
            f"[USERS] Resposta batch: status={response.status_code} "
            f"data={getattr(response, 'data', None)}"
        )

        if response.status_code != status.HTTP_200_OK:
            error_detail = getattr(response, "data", str(response))
            logger.error(f"[USERS] Falha batch aba '{sheet_name}': {error_detail}")
            return []

        logger.info(f"[USERS] {len(users)} usuário(s) confirmado(s) na catraca")
        return users

    def _sync_relations_batch(
        self, users: list[User], grupo: Group, sheet_name: str
    ) -> bool:
        """
        Upsert em batch das relações user_groups em todas as catracas.
        Retorna True se bem-sucedido.
        """
        if not users:
            return True

        self._device = None
        relations_payload = [
            {"user_id": u.id, "group_id": grupo.id} for u in users
        ]

        logger.info(
            f"[RELACAO] Batch upsert de {len(relations_payload)} relação(ões) "
            f"grupo id={grupo.id} name='{grupo.name}'"
        )

        response = self.create_or_update_objects_in_all_devices(
            "user_groups", relations_payload
        )

        logger.info(
            f"[RELACAO] Resposta batch: status={response.status_code} "
            f"data={getattr(response, 'data', None)}"
        )

        if response.status_code != status.HTTP_200_OK:
            error_detail = getattr(response, "data", str(response))
            logger.error(f"[RELACAO] Falha batch aba '{sheet_name}': {error_detail}")
            return False

        return True


    def get(self, request, *args, **kwargs):
        return Response({
            "message": "Upload de arquivo Excel para importação de usuários",
            "instructions": {
                "method": "POST",
                "content_type": "multipart/form-data",
                "field_name": "file",
                "file_format": ".xlsx",
                "sheet_format": "1INFO1(2025), 1AGRO1(2025), 1QUIMI1(2025), etc.",
                "required_columns": REQUIRED_COLUMNS,
            },
            "example": {
                "curl": "curl -X POST -F 'file=@alunos.xlsx' http://localhost:8000/api/control_id/import-users/"
            },
        })

    def post(self, request, *args, **kwargs):
        tmp_path = None
        try:
            file: InMemoryUploadedFile = request.FILES.get("file")
            if not file:
                return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

            if not EXCEL_EXTENSION_PATTERN.match(file.name):
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

            logger.info(f"[IMPORT] Arquivo recebido: {len(sheet_names)} aba(s) → {sheet_names}")

            if not sheet_names:
                return Response(
                    {"error": "No sheets found in the Excel file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            created_users = 0
            updated_users = 0
            created_groups = 0
            updated_groups = 0
            created_relations = 0
            errors = []
            catraca_errors = []

            for sheet_name in sheet_names:
                sheet_name = str(sheet_name).strip()
                logger.info(f"[IMPORT] ── Aba '{sheet_name}' ──")

                df = pd.read_excel(tmp_path, sheet_name=sheet_name)

                if len(df.columns) != 3:
                    msg = f"Sheet '{sheet_name}': esperado 3 colunas (ORDEM, Matrícula, Nome)"
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue

                df.columns = REQUIRED_COLUMNS

                if df.empty:
                    msg = f"Sheet '{sheet_name}': sem dados"
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue

                nome_grupo = self._parse_sheet_name(sheet_name)
                if not nome_grupo:
                    msg = f"Sheet '{sheet_name}': formato inválido. Esperado: '1INFO1(2025)'"
                    logger.warning(f"[IMPORT] {msg}")
                    errors.append(msg)
                    continue

                with transaction.atomic():
                    grupo, err = self._ensure_group(nome_grupo)
                    if err:
                        catraca_errors.append(f"Grupo {nome_grupo}: {err}")
                        continue

                    if Group.objects.filter(name=nome_grupo, id=grupo.id).exists():
                        if created_groups == 0 or grupo.id not in [
                            g.id for g in Group.objects.filter(name=nome_grupo)
                        ]:
                            created_groups += 1
                        else:
                            updated_groups += 1
                    updated_groups += 1

                    rows_valid = []
                    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
                        if pd.isna(row["Matrícula"]) or pd.isna(row["Nome"]):
                            msg = f"Sheet '{sheet_name}', linha {row_number}: Matrícula ou Nome vazio"
                            logger.warning(f"[IMPORT] {msg}")
                            errors.append(msg)
                            continue
                        rows_valid.append({
                            "name": str(row["Nome"]).strip(),
                            "registration": str(row["Matrícula"]).strip(),
                        })

                    if not rows_valid:
                        logger.warning(f"[IMPORT] Aba '{sheet_name}' sem linhas válidas — pulando")
                        continue

                    logger.info(f"[IMPORT] Aba '{sheet_name}': {len(rows_valid)} aluno(s) válido(s)")

                    users_new = []
                    users_existing = []

                    for row in rows_valid:
                        user = User.objects.filter(registration=row["registration"]).first()

                        if not user:

                            email = f"{row['registration']}@escola.edu"
                            user = User.objects.create(
                                name=row["name"],
                                registration=row["registration"],
                                email=email,
                                is_active=True,
                            )
                            logger.info(
                                f"[USER] Criado: id={user.id} "
                                f"name='{user.name}' registration={user.registration}"
                            )
                            users_new.append(user)
                            created_users += 1
                        else:
                            needs_update = (
                                user.name != row["name"]
                                or user.registration != row["registration"]
                                or not user.is_active
                            )
                            if needs_update:
                                logger.info(
                                    f"[USER] Atualizado: id={user.id} "
                                    f"'{user.name}' → '{row['name']}'"
                                )
                                user.name = row["name"]
                                user.registration = row["registration"]
                                user.is_active = True
                                user.save(update_fields=["name", "registration", "is_active"])
                            else:
                                logger.info(f"[USER] Sem alterações: id={user.id} name='{user.name}'")
                            users_existing.append(user)
                            updated_users += 1

                    logger.info(
                        f"[USER] Aba '{sheet_name}': "
                        f"{len(users_new)} novo(s), {len(users_existing)} existente(s)"
                    )

                    all_users = users_new + users_existing
                    synced_users = self._sync_users_batch(all_users, sheet_name)

                    if not synced_users:
                        catraca_errors.append(
                            f"Sheet '{sheet_name}': falha ao sincronizar usuários na catraca — "
                            f"relações não serão criadas"
                        )
                        continue

                    new_relation_users = []
                    for user in synced_users:
                        _, created = UserGroup.objects.get_or_create(user=user, group=grupo)
                        if created:
                            new_relation_users.append(user)
                            created_relations += 1

                    logger.info(
                        f"[RELACAO] {len(new_relation_users)} nova(s) relação(ões) "
                        f"para grupo '{grupo.name}'"
                    )

                    if new_relation_users:
                        success = self._sync_relations_batch(new_relation_users, grupo, sheet_name)
                        if not success:
                            catraca_errors.append(
                                f"Sheet '{sheet_name}': falha ao sincronizar relações na catraca"
                            )

                logger.info(f"[IMPORT] ── Aba '{sheet_name}' concluída ──")

            logger.info(
                f"[IMPORT] Finalizado — "
                f"grupos: +{created_groups} ~{updated_groups} | "
                f"usuários: +{created_users} ~{updated_users} | "
                f"relações: +{created_relations} | "
                f"erros: {len(errors)} | erros catraca: {len(catraca_errors)}"
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        f"Importação concluída. "
                        f"Grupos: {created_groups} criados, {updated_groups} sincronizados. "
                        f"Usuários: {created_users} criados, {updated_users} atualizados. "
                        f"Relações: {created_relations} criadas."
                    ),
                    "sheets_processed": len(sheet_names),
                    "errors": errors or None,
                    "catraca_errors": catraca_errors or None,
                },
                status=status.HTTP_200_OK if not (errors or catraca_errors) else status.HTTP_207_MULTI_STATUS,
            )

        except Exception as e:
            logger.exception(f"[IMPORT] Exceção não tratada: {e}")
            return Response(
                {"error": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass