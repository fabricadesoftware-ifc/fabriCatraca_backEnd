from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status


class GeneralSyncMixin(ControlIDSyncMixin):
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "general",
            {
                "auto_reboot_hour": instance.auto_reboot_hour,
                "auto_reboot_minute": instance.auto_reboot_minute,
                "clear_expired_users": instance.clear_expired_users,
                "url_reboot_enabled": instance.url_reboot_enabled,
                "keep_user_image": instance.keep_user_image,
                "beep_enabled": instance.beep_enabled,
                "ssh_enabled": instance.ssh_enabled,
                "relayN_enabled": instance.relayN_enabled,
                "relayN_timeout": instance.relayN_timeout,
                "relayN_auto_close": instance.relayN_auto_close,
                "door_sensorN_enabled": instance.door_sensorN_enabled,
                "door_sensorN_idle": instance.door_sensorN_idle,
                "doorN_interlock": instance.doorN_interlock,
                "bell_enabled": instance.bell_enabled,
                "bell_relay": instance.bell_relay,
                "catra_timeout": instance.catra_timeout,
                "online": instance.online,
                "local_identification": instance.local_identification,
                "exception_mode": instance.exception_mode,
                "doorN_exception_mode": instance.doorN_exception_mode,
                "language": instance.language,
                "daylight_savings_time_start": instance.daylight_savings_time_start,
                "daylight_savings_time_end": instance.daylight_savings_time_end,
                "password_only": instance.password_only,
                "hide_password_only": instance.hide_password_only,
                "password_only_tip": instance.password_only_tip,
                "hide_name_on_identification": instance.hide_name_on_identification,
                "denied_transaction_code": instance.denied_transaction_code,
                "send_code_when_not_identified": instance.send_code_when_not_identified,
                "send_code_when_not_authorized": instance.send_code_when_not_authorized,
                "screen_always_on": instance.screen_always_on,
                "web_server_enabled": instance.web_server_enabled
            },
        )
        return response
    