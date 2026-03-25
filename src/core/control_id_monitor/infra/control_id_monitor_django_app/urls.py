from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.reverse import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .views import (
    ifc_schedules_proxy,
    MonitorAlertViewSet,
    MonitorConfigViewSet,
    receive_auxiliary_notification,
    receive_catra_event,
    receive_dao_notification,
)

# Router para as views do Monitor
router = DefaultRouter()
router.register(r"monitor-configs", MonitorConfigViewSet, basename="monitorconfig")
router.register(r"alerts", MonitorAlertViewSet, basename="monitoralert")


@api_view(["GET"])
def monitor_root(request, format=None):
    """
    API Root para Control ID Monitor - Sistema de Push de Logs em Tempo Real
    """
    return Response(
        {
            "monitor_configs": reverse(
                "monitorconfig-list", request=request, format=format
            ),
            "alerts": reverse("monitoralert-list", request=request, format=format),
            "dao_webhook": reverse(
                "monitor-dao-notification", request=request, format=format
            ),
        }
    )


urlpatterns = [
    path("", monitor_root, name="monitor-root"),
    path("ifc-schedules/source", ifc_schedules_proxy, name="monitor-ifc-schedules-source"),
    # Endpoint para receber notificações da catraca (PUSH)
    path(
        "notifications/dao", receive_dao_notification, name="monitor-dao-notification"
    ),
    # Endpoints auxiliares enviados pelo firmware após reboot/config change
    path(
        "notifications/operation_mode",
        receive_auxiliary_notification,
        name="monitor-operation-mode",
    ),
    path(
        "notifications/device_is_alive",
        receive_auxiliary_notification,
        name="monitor-device-is-alive",
    ),
    # Endpoint para eventos de giro da catraca (catra_event)
    path(
        "notifications/catra_event",
        receive_catra_event,
        name="monitor-catra-event",
    ),
    # Rotas do ViewSet (CRUD de MonitorConfig)
    path("", include(router.urls)),
]
