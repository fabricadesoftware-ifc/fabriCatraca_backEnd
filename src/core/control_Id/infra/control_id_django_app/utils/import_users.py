import logging
import os
import tempfile

import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .excel_parser import REQUIRED_COLUMNS, is_valid_excel, parse_sheet
from .import_users_service import ImportUsersService

logger = logging.getLogger(__name__)


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text=(
            "Arquivo Excel (.xlsx) com usuários para importar. "
            "Abas no formato '1INFO1(2025)', colunas: ORDEM, Matrícula, Nome"
        )
    )


class ImportUsersView(APIView):
    """
    Importa alunos de um arquivo Excel com múltiplas abas.

    Cada aba representa uma turma (ex: '1INFO1(2025)') e gera:
      - Um Group no Django e em todas as catracas ativas
      - Users vinculados à turma via UserGroup
    """

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileUploadSerializer

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
            tmp_path = self._save_upload(request)
            if isinstance(tmp_path, Response):
                return tmp_path

            sheet_names = self._read_sheet_names(tmp_path)
            if isinstance(sheet_names, Response):
                return sheet_names

            return self._process_sheets(tmp_path, sheet_names)

        except Exception as e:
            logger.exception(f"[IMPORT] Exceção não tratada: {e}")
            return Response(
                {"error": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if tmp_path and not isinstance(tmp_path, Response):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def _save_upload(self, request) -> str | Response:
        """Salva o upload em arquivo temporário. Retorna o path ou um Response de erro."""
        file: InMemoryUploadedFile = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        if not is_valid_excel(file.name):
            return Response(
                {"error": "Invalid file format. Please upload an .xlsx file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp.flush()
            return tmp.name

    def _read_sheet_names(self, tmp_path: str) -> list[str] | Response:
        """Lê os nomes das abas do Excel."""
        excel_file = pd.ExcelFile(tmp_path)
        sheet_names = excel_file.sheet_names
        excel_file.close()

        logger.info(f"[IMPORT] Arquivo recebido: {len(sheet_names)} aba(s) → {sheet_names}")

        if not sheet_names:
            return Response(
                {"error": "No sheets found in the Excel file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return sheet_names

    def _process_sheets(self, tmp_path: str, sheet_names: list[str]) -> Response:
        """Processa todas as abas e retorna o resultado consolidado."""
        service = ImportUsersService()

        created_users = 0
        updated_users = 0
        created_groups = 0
        updated_groups = 0
        created_relations = 0
        errors = []
        catraca_errors = []

        for raw_sheet_name in sheet_names:
            sheet_name = str(raw_sheet_name).strip()
            logger.info(f"[IMPORT] ── Aba '{sheet_name}' ──")

            parsed, parse_error = parse_sheet(tmp_path, sheet_name)

            if parse_error:
                errors.append(parse_error)
                continue
            if parsed is None:
                continue

            with transaction.atomic():
                # Grupo
                grupo, err = service.ensure_group(parsed.group_name)
                if err:
                    catraca_errors.append(f"Grupo {parsed.group_name}: {err}")
                    continue
                updated_groups += 1

                # Usuários
                users_new, users_existing, n_created, n_updated = service.upsert_users(
                    parsed.rows
                )
                created_users += n_created
                updated_users += n_updated

                logger.info(
                    f"[USER] Aba '{sheet_name}': "
                    f"{n_created} novo(s), {n_updated} existente(s)"
                )

                # Sync usuários na catraca
                all_users = users_new + users_existing
                synced_users = service.sync_users_to_devices(all_users, sheet_name)

                if not synced_users:
                    catraca_errors.append(
                        f"Sheet '{sheet_name}': falha ao sincronizar usuários na catraca — "
                        f"relações não serão criadas"
                    )
                    continue

                # Relações user_group
                new_relation_users = service.create_local_relations(synced_users, grupo)
                created_relations += len(new_relation_users)

                if new_relation_users:
                    success = service.sync_relations_to_devices(
                        new_relation_users, grupo, sheet_name
                    )
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
