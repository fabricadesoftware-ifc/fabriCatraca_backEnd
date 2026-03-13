from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.serializers.device_actions import (
    BuzzerBuzzSerializer,
    MessageToScreenSerializer,
    RemoteUserAuthorizationSerializer,
)


def _execute_action(serializer_class, request, endpoint: str, request_timeout: int = 10):
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def remote_user_authorization(request):
    return _execute_action(
        serializer_class=RemoteUserAuthorizationSerializer,
        request=request,
        endpoint="remote_user_authorization.fcgi",
        request_timeout=15,
    )
