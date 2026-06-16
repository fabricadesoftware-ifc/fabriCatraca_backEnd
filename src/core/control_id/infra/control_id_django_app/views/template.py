from __future__ import annotations

import traceback

from typing import Any

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from src.core.__seedwork__.infra.api_errors import api_error_response
from src.core.control_id.infra.control_id_django_app.models import (
    BiometricCaptureSession,
    Device,
    Template,
)
from src.core.control_id.infra.control_id_django_app.serializers.template import (
    TemplateSerializer,
)
from src.core.control_id.infra.control_id_django_app.services import (
    BiometricEnrollmentError,
    BiometricEnrollmentService,
    BiometricTemplateExtractionService,
    TemplateDeviceSyncService,
)
from src.core.control_id.infra.control_id_django_app.use_cases import (
    CompleteLocalCaptureSessionUseCase,
    CreateRemoteTemplateUseCase,
    DeleteTemplateUseCase,
    TemplateOperationError,
    UpdateTemplateUseCase,
)
from src.core.user.infra.user_django_app.models import User


CreateRemoteTemplatePayload = tuple[Template, dict[str, Any]]
CompleteCaptureSessionPayload = tuple[Template, list[dict[str, Any]]]


@extend_schema(tags=["Templates"])
class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filterset_fields = ["user"]

    def _get_user_id(self, request):
        return (
            request.data.get("user_id")
            or request.query_params.get("user_id")
            or request.data.get("user")
        )

    def _serialize_instance(self, instance: Template, extra_data: dict | None = None):
        payload = self.get_serializer(instance).data
        if extra_data:
            payload.update(extra_data)
        return payload

    def _get_active_devices(self):
        return list(Device.objects.filter(is_active=True).order_by("id"))

    def _get_target_devices_for_user(self, user: User):
        return list(user.get_target_devices(include_inactive=False))

    def _get_default_extractor_device(self):
        return (
            Device.objects.filter(is_active=True, is_default=True).first()
            or Device.objects.filter(is_active=True).order_by("id").first()
        )

    def _template_sync_service(self) -> TemplateDeviceSyncService:
        return TemplateDeviceSyncService()

    def _biometric_enrollment_service(self) -> BiometricEnrollmentService:
        return BiometricEnrollmentService()

    def _template_extraction_service(self) -> BiometricTemplateExtractionService:
        return BiometricTemplateExtractionService()

    def _expire_stale_sessions(self):
        stale_sessions = BiometricCaptureSession.objects.filter(
            status__in=[
                BiometricCaptureSession.STATUS_PENDING,
                BiometricCaptureSession.STATUS_PROCESSING,
            ],
            expires_at__lt=timezone.now(),
        )
        stale_sessions.update(
            status=BiometricCaptureSession.STATUS_EXPIRED,
            finished_at=timezone.now(),
            error_message="Sessao expirada antes do envio do template.",
        )

    def _replicate_template_to_active_devices(self, instance: Template):
        return self._template_sync_service().replicate_template_to_user_devices(
            instance
        )

    def _create_remote_template(
        self,
        *,
        user_id: int,
        enrollment_device: Device,
    ) -> Response | CreateRemoteTemplatePayload:
        user = get_object_or_404(User, id=user_id)
        serializer = self.get_serializer(
            data={
                "user_id": user_id,
                "enrollment_device_id": enrollment_device.pk,
            }
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = CreateRemoteTemplateUseCase(
                enrollment_service=self._biometric_enrollment_service(),
                template_sync_service=self._template_sync_service(),
            ).execute(
                serializer,
                user=user,
                enrollment_device=enrollment_device,
            )
        except BiometricEnrollmentError as exc:
            return api_error_response(
                exc.message,
                code=exc.code,
                details=exc.details,
                status_code=exc.status_code,
            )
        except TemplateOperationError as exc:
            return api_error_response(
                exc.message,
                code=exc.code,
                details=exc.details,
                status_code=exc.status_code,
            )

        return result.template, {
            "capture_mode": "catraca",
            "enrollment_device": {
                "id": enrollment_device.pk,
                "name": enrollment_device.name,
            },
            "replication_errors": result.replication_errors or [],
        }

    def _check_device_api_key(self, request):
        sent_key = request.headers.get("X-Bio-Device-Key") or request.query_params.get(
            "api_key"
        )
        expected_key = getattr(settings, "BIOMETRIC_DEVICE_API_KEY", "")
        return bool(expected_key) and sent_key == expected_key

    def _expand_packed_fingerprint_image(self, packed_image: bytes) -> bytes:
        return self._template_extraction_service().expand_packed_fingerprint_image(
            packed_image
        )

    def _extract_template_from_raw_capture(
        self, session: BiometricCaptureSession, packed_image: bytes
    ):
        return self._template_extraction_service().extract_template_from_raw_capture(
            session,
            packed_image,
        )

    def _append_capture_attempt(
        self,
        session: BiometricCaptureSession,
        *,
        attempt_number: int,
        total_attempts: int,
        packed_image: bytes,
    ):
        extracted = self._extract_template_from_raw_capture(session, packed_image)
        attempts = list(session.attempts or [])
        attempts = [
            item
            for item in attempts
            if int(item.get("attempt", 0) or 0) != attempt_number
        ]
        attempts.append(
            {
                "attempt": attempt_number,
                "quality": extracted["quality"],
                "template": extracted["template"],
                "selected": False,
            }
        )
        attempts.sort(key=lambda item: int(item.get("attempt", 0) or 0))

        session.status = (
            BiometricCaptureSession.STATUS_PROCESSING
            if attempt_number < total_attempts
            else session.status
        )
        session.attempts = attempts
        session.error_message = ""
        session.save(
            update_fields=["status", "attempts", "error_message", "updated_at"]
        )
        return attempts

    def _serialize_capture_session(self, session: BiometricCaptureSession):
        attempts = []
        for attempt in session.attempts or []:
            attempts.append(
                {
                    "attempt": attempt.get("attempt"),
                    "quality": attempt.get("quality"),
                    "selected": attempt.get("selected", False),
                }
            )
        return {
            "id": session.pk,
            "user_id": session.user.pk,
            "status": session.status,
            "sensor_identifier": session.sensor_identifier,
            "selected_quality": session.selected_quality,
            "error_message": session.error_message,
            "attempts": attempts,
            "expires_at": session.expires_at,
            "finished_at": session.finished_at,
            "template_id": session.template.pk if session.template_id else None,
            "extractor_device": (
                {
                    "id": session.extractor_device.pk,
                    "name": session.extractor_device.name,
                }
                if session.extractor_device_id
                else None
            ),
        }

    def _complete_capture_session(
        self,
        session: BiometricCaptureSession,
        *,
        template_value: str,
        quality: int | None,
        attempts: list[dict],
    ) -> CompleteCaptureSessionPayload:
        serializer = self.get_serializer(data={"user_id": session.user.pk})
        serializer.is_valid(raise_exception=True)
        result = CompleteLocalCaptureSessionUseCase(
            template_sync_service=self._template_sync_service(),
        ).execute(
            serializer,
            session=session,
            template_value=template_value,
            quality=quality,
            attempts=attempts,
        )
        return result.template, result.replication_errors or []

    def create(self, request, *args, **kwargs):
        try:
            capture_mode = str(request.data.get("capture_mode") or "catraca").lower()
            user_id = self._get_user_id(request)

            if not user_id:
                return Response(
                    {"error": "Usuario (user_id) e obrigatorio"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if capture_mode == "local":
                return Response(
                    {
                        "error": (
                            "Para biometria local use o fluxo de sessao "
                            "em /templates/local-capture/start/."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            enrollment_device_id = request.data.get("enrollment_device_id")
            if not enrollment_device_id:
                return Response(
                    {
                        "error": (
                            "E necessario especificar uma catraca para cadastro "
                            "(enrollment_device_id)"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            enrollment_device = get_object_or_404(Device, id=enrollment_device_id)
            user = get_object_or_404(User, id=int(user_id))
            target_device_ids = {
                device.pk for device in self._get_target_devices_for_user(user)
            }
            if not target_device_ids:
                return Response(
                    {"error": "Usuario nao possui catracas alvo para biometria."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if enrollment_device.pk not in target_device_ids:
                return Response(
                    {
                        "error": "A catraca escolhida nao faz parte do escopo do usuario."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            remote_template_result = self._create_remote_template(
                user_id=int(user_id),
                enrollment_device=enrollment_device,
            )
            if isinstance(remote_template_result, Response):
                return remote_template_result

            instance, extra_payload = remote_template_result

            return Response(
                self._serialize_instance(instance, extra_payload),
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            traceback.print_exc()
            return Response(
                {
                    "error": "Erro interno no servidor ao processar biometria",
                    "details": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="local-capture/start")
    def start_local_capture(self, request):
        user_id = self._get_user_id(request)
        if not user_id:
            return Response(
                {"error": "Usuario (user_id) e obrigatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, id=int(user_id))
        target_device_ids = {
            device.pk for device in self._get_target_devices_for_user(user)
        }
        if not target_device_ids:
            return Response(
                {"error": "Usuario nao possui catracas alvo para biometria."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extractor_device_id = request.data.get("extractor_device_id")
        sensor_identifier = str(
            request.data.get("sensor_identifier") or "local-default"
        ).strip()
        if not sensor_identifier:
            return Response(
                {"error": "sensor_identifier e obrigatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if extractor_device_id:
            extractor_device = get_object_or_404(
                Device,
                id=extractor_device_id,
                is_active=True,
            )
            if extractor_device.pk not in target_device_ids:
                return Response(
                    {
                        "error": "A catraca extratora nao faz parte do escopo do usuario."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            extractor_device = next(
                (
                    device
                    for device in self._get_target_devices_for_user(user)
                    if device.is_active
                ),
                None,
            )

        if extractor_device is None:
            return Response(
                {"error": "Nenhuma catraca ativa disponivel para extrair o template"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        BiometricCaptureSession.objects.filter(
            user_id=user_id,
            status__in=[
                BiometricCaptureSession.STATUS_PENDING,
                BiometricCaptureSession.STATUS_PROCESSING,
            ],
        ).update(
            status=BiometricCaptureSession.STATUS_CANCELLED,
            finished_at=timezone.now(),
            error_message="Sessao anterior cancelada por nova solicitacao.",
        )

        session = BiometricCaptureSession.objects.create(
            user_id=user_id,
            requested_by=request.user if request.user.is_authenticated else None,
            extractor_device=extractor_device,
            sensor_identifier=sensor_identifier,
        )

        return Response(
            {
                "message": "Sessao de captura local iniciada.",
                "capture_session": self._serialize_capture_session(session),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"local-capture/(?P<session_id>\d+)/status",
    )
    def local_capture_status(self, request, session_id=None):
        self._expire_stale_sessions()
        session = get_object_or_404(BiometricCaptureSession, id=session_id)
        return Response({"capture_session": self._serialize_capture_session(session)})

    @action(
        detail=False,
        methods=["get"],
        url_path="local-capture/pending",
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def pending_local_capture(self, request):
        if not self._check_device_api_key(request):
            return Response(
                {"error": "Chave do dispositivo invalida"},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._expire_stale_sessions()
        sensor_identifier = str(
            request.query_params.get("sensor_identifier") or "local-default"
        ).strip()
        session = (
            BiometricCaptureSession.objects.select_related("extractor_device")
            .filter(
                sensor_identifier=sensor_identifier,
                status=BiometricCaptureSession.STATUS_PENDING,
                expires_at__gte=timezone.now(),
            )
            .order_by("created_at")
            .first()
        )

        if session is None:
            return Response({"capture_available": False})

        extractor = session.extractor_device
        return Response(
            {
                "capture_available": True,
                "capture_session_id": session.pk,
                "capture_token": str(session.token),
                "user_id": session.user.pk,
                "sensor_identifier": session.sensor_identifier,
                "extractor_device": {
                    "id": extractor.pk,
                    "name": extractor.name,
                    "ip": extractor.ip,
                    "username": extractor.username,
                    "password": extractor.password,
                },
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"local-capture/(?P<session_id>\d+)/upload-raw",
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def upload_local_capture_raw(self, request, session_id=None):
        if not self._check_device_api_key(request):
            return Response(
                {"error": "Chave do dispositivo invalida"},
                status=status.HTTP_403_FORBIDDEN,
            )

        self._expire_stale_sessions()
        session = get_object_or_404(BiometricCaptureSession, id=session_id)

        if session.is_expired:
            session.status = BiometricCaptureSession.STATUS_EXPIRED
            session.finished_at = timezone.now()
            session.error_message = "Sessao expirada antes da entrega do template."
            session.save(
                update_fields=["status", "finished_at", "error_message", "updated_at"]
            )
            return Response({"error": "Sessao expirada"}, status=status.HTTP_410_GONE)

        capture_token = str(
            request.headers.get("X-Capture-Token")
            or request.query_params.get("capture_token")
            or ""
        )
        if str(session.token) != capture_token:
            return Response(
                {"error": "Token de captura invalido"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            attempt_number = int(request.query_params.get("attempt") or 0)
            total_attempts = int(request.query_params.get("total_attempts") or 3)
        except ValueError:
            return Response(
                {"error": "attempt e total_attempts devem ser inteiros"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            attempt_number <= 0
            or total_attempts <= 0
            or attempt_number > total_attempts
        ):
            return Response(
                {"error": "Sequencia de tentativas invalida"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        packed_image = request.body or b""
        if not packed_image:
            return Response(
                {"error": "Corpo binario com imagem bruta e obrigatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            attempts = self._append_capture_attempt(
                session,
                attempt_number=attempt_number,
                total_attempts=total_attempts,
                packed_image=packed_image,
            )
        except Exception as exc:
            session.status = BiometricCaptureSession.STATUS_FAILED
            session.finished_at = timezone.now()
            session.error_message = str(exc)
            session.save(
                update_fields=["status", "finished_at", "error_message", "updated_at"]
            )
            traceback.print_exc()
            return Response(
                {"error": "Falha ao processar imagem biometrica", "details": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if attempt_number < total_attempts:
            return Response(
                {
                    "success": True,
                    "completed": False,
                    "capture_session": self._serialize_capture_session(session),
                }
            )

        best_attempt = max(attempts, key=lambda item: int(item.get("quality", 0) or 0))
        best_template_value = str(best_attempt["template"])
        for attempt in attempts:
            attempt["selected"] = attempt["attempt"] == best_attempt["attempt"]
            attempt.pop("template", None)

        try:
            instance, replication_errors = self._complete_capture_session(
                session,
                template_value=best_template_value,
                quality=int(best_attempt.get("quality", 0) or 0),
                attempts=attempts,
            )
        except Exception as exc:
            session.status = BiometricCaptureSession.STATUS_FAILED
            session.finished_at = timezone.now()
            session.error_message = str(exc)
            session.save(
                update_fields=["status", "finished_at", "error_message", "updated_at"]
            )
            traceback.print_exc()
            return Response(
                {"error": "Falha ao concluir sessao de captura", "details": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "completed": True,
                "template": self._serialize_instance(
                    instance,
                    {
                        "capture_mode": "local",
                        "best_quality": session.selected_quality,
                        "attempts": session.attempts,
                        "replication_errors": replication_errors,
                    },
                ),
            }
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            result = UpdateTemplateUseCase(
                template_sync_service=self._template_sync_service(),
            ).execute(serializer)
        except Exception as exc:
            return api_error_response(
                "Erro ao atualizar biometria na catraca.",
                code="template_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(self.get_serializer(result.template).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            DeleteTemplateUseCase(
                template_sync_service=self._template_sync_service(),
            ).execute(instance)
        except Exception as exc:
            return api_error_response(
                "Erro ao deletar biometria da catraca.",
                code="template_sync_failed",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
