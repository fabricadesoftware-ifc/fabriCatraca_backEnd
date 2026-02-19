from django.urls import include, path
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .views import (
    SystemConfigViewSet,
    HardwareConfigViewSet,
    SecurityConfigViewSet,
    UIConfigViewSet,
    DeviceConfigView,
    easy_setup,
)
from .views.catra_config import CatraConfigViewSet
from .views.push_server_config import PushServerConfigViewSet
from .views.sync import sync_all_configs, sync_config_status, sync_device_config

router = DefaultRouter()
router.register(r'system-configs', SystemConfigViewSet)
router.register(r'hardware-configs', HardwareConfigViewSet)
router.register(r'security-configs', SecurityConfigViewSet)
router.register(r'ui-configs', UIConfigViewSet)
router.register(r'catra-configs', CatraConfigViewSet)
router.register(r'push-server-configs', PushServerConfigViewSet)


@api_view(['GET'])
def config_root(request, format=None):
    return Response({
        'system_configs': reverse('systemconfig-list', request=request, format=format),
        'hardware_configs': reverse('hardwareconfig-list', request=request, format=format),
        'security_configs': reverse('securityconfig-list', request=request, format=format),
        'ui_configs': reverse('uiconfig-list', request=request, format=format),
        'catra_configs': reverse('catraconfig-list', request=request, format=format),
        'push_server_configs': reverse('pushserverconfig-list', request=request, format=format),
        'easy_setup': reverse('easy-setup', request=request, format=format),
        'sync_all_configs': reverse('sync-all-configs', request=request, format=format),
        'sync_config_status': reverse('sync-config-status', request=request, format=format),
        'monitor_configs': 'Moved to /api/control_id_monitor/monitor-configs/',
    })

urlpatterns = [
    path('', config_root, name='config-root'),
    path('easy-setup/', easy_setup, name='easy-setup'),
    path('sync/', sync_all_configs, name='sync-all-configs'),
    path('sync/status/', sync_config_status, name='sync-config-status'),
    path('device-config/<int:device_id>/', sync_device_config, name='sync-device-config'),
    path('', include(router.urls)),
]