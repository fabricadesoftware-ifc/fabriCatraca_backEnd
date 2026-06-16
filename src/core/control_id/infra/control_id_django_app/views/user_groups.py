import pandas as pd
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models import (
    CustomGroup,
    UserGroup,
)
from src.core.control_id.infra.control_id_django_app.serializers import (
    UserGroupSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    UserGroupDeviceSyncService,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CreateUserGroupUseCase,
    DeleteUserGroupUseCase,
    UpdateUserGroupUseCase,
)
from src.core.user.infra.user_django_app.models import User


class UserGroupImportSerializer(serializers.Serializer):
    """Serializer para importacao de usuarios em grupo."""

    file = serializers.FileField(
        help_text=(
            "Arquivo Excel (.xlsx) com usuarios para importar. Deve conter "
            "colunas 'Matricula' e 'Nome'."
        )
    )
    group_id = serializers.IntegerField(
        help_text="ID do grupo para adicionar os usuarios"
    )

    def validate(self, attrs):
        try:
            CustomGroup.objects.get(id=attrs["group_id"])
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError({"group_id": "Grupo nao encontrado"})

        file = attrs.get("file")
        if not file:
            raise serializers.ValidationError({"file": "Arquivo e obrigatorio"})

        if not file.name.lower().endswith((".xls", ".xlsx")):
            raise serializers.ValidationError(
                {"file": "Formato de arquivo invalido. Use .xlsx"}
            )

        return attrs


class UserGroupViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de vinculos entre usuarios e grupos."""

    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    filterset_fields = ["user", "group"]
    search_fields = ["user__name", "group__name"]
    ordering_fields = ["user__name", "group__name"]

    def _user_group_sync_service(self) -> UserGroupDeviceSyncService:
        return UserGroupDeviceSyncService()

    @staticmethod
    def _build_sync_error_response(exc: Exception) -> Response:
        return api_error_response(
            "Erro ao sincronizar vinculo de usuario e grupo na catraca.",
            code="user_group_sync_failed",
            details=str(exc),
            status_code=getattr(exc, "status_code", None)
            or status.HTTP_400_BAD_REQUEST,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateUserGroupUseCase(
                sync_service=self._user_group_sync_service(),
            ).execute(serializer)
        except Exception as exc:
            return self._build_sync_error_response(exc)

        return Response(
            self.get_serializer(result.instance).data,
            status=result.status_code,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            instance = UpdateUserGroupUseCase(
                sync_service=self._user_group_sync_service(),
            ).execute(instance, serializer)
        except Exception as exc:
            return self._build_sync_error_response(exc)

        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteUserGroupUseCase(
                sync_service=self._user_group_sync_service(),
            ).execute(instance)
        except Exception as exc:
            return self._build_sync_error_response(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Importar usuarios para um grupo",
        description=(
            "Importa usuarios de um arquivo Excel para um grupo especifico. "
            "Usuarios sao buscados pela matricula e usuarios ja vinculados "
            "ao grupo sao ignorados."
        ),
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "group_id": {"type": "integer"},
                },
            }
        },
        responses={
            200: {"description": "Importacao bem-sucedida"},
            207: {"description": "Importacao parcial com erros"},
            400: {"description": "Erro de validacao do arquivo"},
            404: {"description": "Nenhum usuario encontrado"},
        },
    )
    @action(
        detail=False,
        methods=["POST"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=UserGroupImportSerializer,
    )
    def import_users(self, request):
        if not request.FILES:
            return Response(
                {
                    "error": "Nenhum arquivo enviado",
                    "details": "request.FILES esta vazio",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as exc:
            return Response(
                {
                    "error": "Erro de validacao",
                    "details": str(exc),
                    "validation_errors": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        group = CustomGroup.objects.get(id=serializer.validated_data["group_id"])

        try:
            df = pd.read_excel(file)
        except Exception as exc:
            return Response(
                {
                    "error": f"Erro ao ler arquivo Excel: {str(exc)}",
                    "details": {
                        "filename": file.name,
                        "file_size": file.size,
                        "file_type": file.content_type,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_columns = {"Matricula", "Nome"}
        column_aliases = {
            "Matricula": ("Matricula", "Matrícula", "MATRICULA"),
            "Nome": ("Nome", "NOME", "NOME_COMPLETO"),
        }
        resolved_columns = {
            target: next((name for name in names if name in df.columns), None)
            for target, names in column_aliases.items()
        }
        if any(column is None for column in resolved_columns.values()):
            return Response(
                {
                    "error": (
                        "Colunas obrigatorias ausentes. Esperado: "
                        f"{sorted(required_columns)}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stats = {
            "total_usuarios": len(df),
            "usuarios_adicionados": 0,
            "usuarios_ja_existentes": 0,
            "usuarios_nao_encontrados": 0,
            "erros": [],
        }

        sync_service = self._user_group_sync_service()
        registration_column = resolved_columns["Matricula"]
        name_column = resolved_columns["Nome"]

        with transaction.atomic():
            for _, row in df.iterrows():
                registration = ""
                name = ""
                try:
                    registration = str(row[registration_column]).strip()
                    name = str(row[name_column]).strip()

                    user = User.objects.filter(registration=registration).first()

                    if not user:
                        stats["usuarios_nao_encontrados"] += 1
                        stats["erros"].append(
                            f"Usuario nao encontrado: {registration} - {name}"
                        )
                        continue

                    existing_group = UserGroup.objects.filter(
                        user=user,
                        group=group,
                    ).exists()
                    if existing_group:
                        stats["usuarios_ja_existentes"] += 1
                        continue

                    instance = UserGroup.objects.create(user=user, group=group)

                    try:
                        sync_service.create(instance)
                    except Exception as sync_err:
                        stats["erros"].append(
                            "Usuario "
                            f"{registration} salvo localmente, erro sync catraca: "
                            f"{str(sync_err)}"
                        )

                    stats["usuarios_adicionados"] += 1

                except Exception as exc:
                    stats["erros"].append(
                        f"Erro ao processar {registration} - {name}: {str(exc)}"
                    )

        response_data = {
            "message": "Importacao de usuarios concluida",
            "estatisticas": stats,
        }

        if stats["usuarios_nao_encontrados"] == stats["total_usuarios"]:
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        if stats["erros"]:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        return Response(response_data, status=status.HTTP_200_OK)
