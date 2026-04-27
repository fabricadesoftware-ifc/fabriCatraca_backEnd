from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_id.infra.control_id_django_app.serializers.device_actions import (
    BuzzerBuzzSerializer,
    MessageToScreenSerializer,
    RemoteUserAuthorizationSerializer,
)
from src.core.control_id.infra.control_id_django_app.release_audit_service import (
    ReleaseAuditService,
)
from src.core.user.infra.user_django_app.permissions import (
    IsAdminOrGuaritaRole,
    IsAdminRole,
)


def _execute_action(
    serializer_class, request, endpoint: str, request_timeout: int = 10
):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)

    payload = dict(serializer.validated_data)
    device_ids = payload.pop("device_ids")

    sync = ControlIDSyncMixin()
    return sync.execute_remote_endpoint_in_devices(
        endpoint=endpoint,
        payload=payload,
        device_ids=device_ids,
        request_timeout=request_timeout,
    )


@extend_schema(
    tags=["Devices"],
    request=MessageToScreenSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAdminRole])
def message_to_screen(request):
    return _execute_action(
        serializer_class=MessageToScreenSerializer,
        request=request,
        endpoint="message_to_screen.fcgi",
    )


@extend_schema(
    tags=["Devices"],
    request=BuzzerBuzzSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAdminRole])
def buzzer_buzz(request):
    return _execute_action(
        serializer_class=BuzzerBuzzSerializer,
        request=request,
        endpoint="buzzer_buzz.fcgi",
    )


@extend_schema(
    tags=["Devices"],
    request=RemoteUserAuthorizationSerializer,
    responses={200: dict},
)
@api_view(["POST"])
@permission_classes([IsAdminOrGuaritaRole])
def remote_user_authorization(request):
    serializer = RemoteUserAuthorizationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    validated_payload = dict(serializer.validated_data)
    device_ids = validated_payload.pop("device_ids")
    validated_payload.pop("notes", None)
    validated_payload.pop("release_mode", None)

    sync = ControlIDSyncMixin()
    response = sync.execute_remote_endpoint_in_devices(
        endpoint="remote_user_authorization.fcgi",
        payload=validated_payload,
        device_ids=device_ids,
        request_timeout=15,
    )
    ReleaseAuditService.create_remote_authorization(
        requested_by=request.user,
        payload=dict(serializer.validated_data),
        response=response,
    )
    return response
