from django.urls import path
from .views.device_config_view import DeviceConfigView

urlpatterns = [
    path('device/<int:device_id>/config/', DeviceConfigView.as_view(), name='device-config'),
]


