import logging
import os
import tempfile
import time

import pandas as pd
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .excel_parser import (
    CSV_REQUIRED_COLUMNS,
    REQUIRED_COLUMNS,
    is_valid_csv,
    is_valid_excel,
    parse_discente_csv,
    parse_sheet,
)
from .import_users_service import ImportUsersService

logger = logging.getLogger(__name__)

IMPORT_PROFILE_GROUPS = {
    "tecnico_integrado": "Tecnico Integrado",
    "graduacao": "Graduacao",
    "servidores": "Servidores",
    "tecnico_subsequente": "Tecnico Subsequente",
}
IMPORT_PROFILE_APP_ROLES = {
    "tecnico_integrado": "aluno",
    "graduacao": "aluno",
    "servidores": "servidor",
    "tecnico_subsequente": "aluno",
}
TURMA_PROFILE = "tecnico_integrado"


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

    def _finalize_response(self, response: Response, start_time: float) -> Response:
        """Anexa a duracao total da importacao e registra o desfecho."""
        elapsed_s = round(time.perf_counter() - start_time, 2)

        if isinstance(getattr(response, "data", None), dict):
            response.data["elapsed_s"] = elapsed_s

        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "[IMPORT] Requisicao finalizada status=%s elapsed_s=%.2f",
            response.status_code,
            elapsed_s,
        )
        return response

    def get(self, request, *args, **kwargs):
        return Response({
            "message": "Upload de arquivo Excel para importação de usuários",
            "instructions": {
                "method": "POST",
                "content_type": "multipart/form-data",
                "field_name": "file",
                "file_format": ".xlsx ou .csv",
                "sheet_format": "1INFO1(2025), 1AGRO1(2025), 1QUIMI1(2025), etc.",
                "required_columns": REQUIRED_COLUMNS,
                "csv_required_columns": CSV_REQUIRED_COLUMNS,
                "import_profiles": list(IMPORT_PROFILE_GROUPS.keys()),
            },
            "example": {
                "curl": "curl -X POST -F 'file=@alunos.xlsx' http://localhost:8000/api/control_id/import-users/"
            },
        })

    def post(self, request, *args, **kwargs):
        start_time = time.perf_counter()
        tmp_path = None
        try:
            upload_info = self._save_upload(request)
            if isinstance(upload_info, Response):
                return self._finalize_response(upload_info, start_time)

            tmp_path, file_kind = upload_info
            import_profile = self._get_import_profile(request)
            if isinstance(import_profile, Response):
                return self._finalize_response(import_profile, start_time)

            if file_kind == "csv":
                return self._finalize_response(
                    self._process_csv(tmp_path, import_profile), start_time
                )

            sheet_names = self._read_sheet_names(tmp_path)
            if isinstance(sheet_names, Response):
                return self._finalize_response(sheet_names, start_time)

            if import_profile == TURMA_PROFILE:
                return self._finalize_response(
                    self._process_sheets(tmp_path, sheet_names), start_time
                )

            return self._finalize_response(
                self._process_generic_excel(tmp_path, sheet_names, import_profile),
                start_time,
            )

        except Exception as e:
            logger.exception(f"[IMPORT] Exceção não tratada: {e}")
            return self._finalize_response(
                Response(
                    {"error": f"Erro ao processar arquivo: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ),
                start_time,
            )

        finally:
            if tmp_path and not isinstance(tmp_path, Response):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def _save_upload(self, request) -> tuple[str, str] | Response:
        """Salva o upload em arquivo temporário. Retorna o path ou um Response de erro."""
        file: InMemoryUploadedFile = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        if is_valid_excel(file.name):
            file_kind = "excel"
            suffix = ".xlsx"
        elif is_valid_csv(file.name):
            file_kind = "csv"
            suffix = ".csv"
        else:
            return Response(
                {"error": "Invalid file format. Please upload an .xlsx or .csv file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp.flush()
            return tmp.name, file_kind

    def _get_import_profile(self, request) -> str | Response:
        import_profile = request.data.get("import_profile", TURMA_PROFILE)
        if import_profile not in IMPORT_PROFILE_GROUPS:
            return Response(
                {
                    "error": (
                        "Perfil de importacao invalido. Use: "
                        f"{', '.join(IMPORT_PROFILE_GROUPS.keys())}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return import_profile

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

    def _process_csv(self, tmp_path: str, import_profile: str) -> Response:
        """Processa CSV/TSV de discentes e cadastra usuarios no grupo do perfil."""
        service = ImportUsersService()
        errors = []
        catraca_errors = []

        parsed, parse_error = parse_discente_csv(tmp_path)
        if parse_error:
            errors.append(parse_error)
        if parsed is None:
            return Response(
                {
                    "success": False,
                    "message": "CSV nao importado.",
                    "errors": errors or None,
                    "catraca_errors": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_users, updated_users, created_relations = self._upsert_users_in_group(
            service,
            parsed.rows,
            IMPORT_PROFILE_GROUPS[import_profile],
            IMPORT_PROFILE_APP_ROLES[import_profile],
            "CSV",
            catraca_errors,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Importacao CSV concluida. "
                    f"Usuarios: {created_users} criados, {updated_users} atualizados. "
                    f"Relacoes: {created_relations} criadas."
                ),
                "rows_processed": len(parsed.rows),
                "errors": errors or None,
                "catraca_errors": catraca_errors or None,
            },
            status=status.HTTP_200_OK if not catraca_errors else status.HTTP_207_MULTI_STATUS,
        )

    def _process_generic_excel(
        self, tmp_path: str, sheet_names: list[str], import_profile: str
    ) -> Response:
        """Processa todas as abas em um unico grupo generico."""
        service = ImportUsersService()
        errors = []
        catraca_errors = []
        rows = []

        for raw_sheet_name in sheet_names:
            sheet_name = str(raw_sheet_name).strip()
            parsed, parse_error = parse_sheet(tmp_path, sheet_name)

            if parse_error:
                errors.append(parse_error)
                continue
            if parsed is None:
                continue
            rows.extend(parsed.rows)

        if not rows:
            return Response(
                {
                    "success": False,
                    "message": "Arquivo nao importado.",
                    "errors": errors or ["Nenhuma linha valida encontrada."],
                    "catraca_errors": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_users, updated_users, created_relations = self._upsert_users_in_group(
            service,
            rows,
            IMPORT_PROFILE_GROUPS[import_profile],
            IMPORT_PROFILE_APP_ROLES[import_profile],
            "Excel",
            catraca_errors,
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Importacao concluida. "
                    f"Usuarios: {created_users} criados, {updated_users} atualizados. "
                    f"Relacoes: {created_relations} criadas."
                ),
                "sheets_processed": len(sheet_names),
                "rows_processed": len(rows),
                "errors": errors or None,
                "catraca_errors": catraca_errors or None,
            },
            status=status.HTTP_200_OK if not (errors or catraca_errors) else status.HTTP_207_MULTI_STATUS,
        )

    def _upsert_users_in_group(
        self,
        service: ImportUsersService,
        rows,
        group_name: str,
        app_role: str,
        source_name: str,
        catraca_errors: list[str],
    ) -> tuple[int, int, int]:
        with transaction.atomic():
            grupo, err = service.ensure_group(group_name)
            if err:
                catraca_errors.append(f"Grupo {group_name}: {err}")
                return 0, 0, 0

            users_new, users_existing, created_users, updated_users = service.upsert_users(
                rows,
                app_role=app_role,
            )
            all_users = users_new + users_existing
            synced_users = service.sync_users_to_devices(all_users, source_name)
            if not synced_users:
                catraca_errors.append(
                    f"{source_name}: falha ao sincronizar usuarios na catraca"
                )
                return created_users, updated_users, 0

            new_relation_users = service.create_local_relations(synced_users, grupo)
            if new_relation_users:
                success = service.sync_relations_to_devices(
                    new_relation_users,
                    grupo,
                    source_name,
                )
                if not success:
                    catraca_errors.append(
                        f"{source_name}: falha ao sincronizar relacoes na catraca"
                    )

        return created_users, updated_users, len(new_relation_users)

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
