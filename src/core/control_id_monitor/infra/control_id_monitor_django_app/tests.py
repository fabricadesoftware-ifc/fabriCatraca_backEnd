from django.test import TestCase
from django.utils import timezone

from src.core.control_id.infra.control_id_django_app.models import Device

from .models import MonitorAlert, MonitorConfig
from .monitoring import mark_monitor_config_offline, touch_device_heartbeat


class MonitorHeartbeatStateTests(TestCase):
    def setUp(self):
        self.device = Device.objects.create(
            name="Catraca monitorada",
            ip="127.0.0.1",
            username="admin",
            password="admin",
            is_active=True,
            is_default=True,
        )
        self.config = MonitorConfig.objects.create(
            device=self.device,
            hostname="127.0.0.1",
            port="8000",
            path="api/notifications",
            heartbeat_timeout_seconds=300,
        )

    def test_offline_auto_disables_active_device(self):
        mark_monitor_config_offline(self.config, detected_at=timezone.now())

        self.device.refresh_from_db()
        self.config.refresh_from_db()

        self.assertFalse(self.device.is_active)
        self.assertTrue(self.config.is_offline)
        self.assertTrue(self.config.auto_disabled_due_to_offline)
        self.assertTrue(
            MonitorAlert.objects.filter(
                device=self.device,
                type=MonitorAlert.AlertType.DEVICE_OFFLINE,
                is_active=True,
            ).exists()
        )

    def test_alive_reactivates_only_device_auto_disabled_by_offline(self):
        mark_monitor_config_offline(self.config, detected_at=timezone.now())

        touch_device_heartbeat(self.device.id, source="alive")

        self.device.refresh_from_db()
        self.config.refresh_from_db()

        self.assertTrue(self.device.is_active)
        self.assertFalse(self.config.is_offline)
        self.assertFalse(self.config.auto_disabled_due_to_offline)
        self.assertFalse(
            MonitorAlert.objects.filter(
                device=self.device,
                type=MonitorAlert.AlertType.DEVICE_OFFLINE,
                is_active=True,
            ).exists()
        )

    def test_alive_does_not_reactivate_manually_inactive_device(self):
        self.device.is_active = False
        self.device.save(update_fields=["is_active"])

        mark_monitor_config_offline(self.config, detected_at=timezone.now())
        touch_device_heartbeat(self.device.id, source="alive")

        self.device.refresh_from_db()
        self.config.refresh_from_db()

        self.assertFalse(self.device.is_active)
        self.assertFalse(self.config.auto_disabled_due_to_offline)
