from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.reverse import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .views import MonitorConfigViewSet, receive_dao_notification

# Router para as views do Monitor
router = DefaultRouter()
router.register(r'monitor-configs', MonitorConfigViewSet, basename='monitorconfig')


@api_view(['GET'])
def monitor_root(request, format=None):
    """
    API Root para Control ID Monitor - Sistema de Push de Logs em Tempo Real
    """
    return Response({
        'monitor_configs': reverse('monitorconfig-list', request=request, format=format),
        'dao_webhook': reverse('monitor-dao-notification', request=request, format=format),
    })


urlpatterns = [
    path('', monitor_root, name='monitor-root'),

    # Endpoint para receber notificações da catraca (PUSH)
    path('notifications/dao', receive_dao_notification, name='monitor-dao-notification'),

    # Rotas do ViewSet (CRUD de MonitorConfig)
    path('', include(router.urls)),
]

