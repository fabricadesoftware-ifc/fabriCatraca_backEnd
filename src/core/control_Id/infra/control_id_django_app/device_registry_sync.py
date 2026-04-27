import logging
from typing import Iterable

import requests

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_id.infra.control_id_django_app.models import Device

logger = logging.getLogger(__name__)


class DeviceRegistrySyncService:
    OBJECT_NAME = "devices"
    FIELDS = ["id", "name", "ip"]

    def __init__(self):
        self.sync = ControlIDSyncMixin()

    def _desired_values(self):
        return [
            {"id": device.id, "name": device.name, "ip": device.ip}
            for device in Device.objects.filter(is_active=True).order_by("id")
        ]

    def _normalize_rows(self, rows):
        normalized = {}
        for row in rows or []:
            try:
                row_id = int(row.get("id"))
            except (TypeError, ValueError):
                continue
            normalized[row_id] = {
                "id": row_id,
                "name": str(row.get("name") or ""),
                "ip": str(row.get("ip") or ""),
            }
        return normalized

    def _post(self, endpoint, payload):
        sess = self.sync.login()
        response = requests.post(
            self.sync.get_url(f"{endpoint}?session={sess}"),
            json=payload,
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(response.text)
        return response

    def sync_target_device(self, target_device, desired_values=None):
        desired_values = desired_values or self._desired_values()
        desired_by_id = {int(item["id"]): item for item in desired_values}

        self.sync.set_device(target_device)
        current_rows = self.sync.load_objects(
            self.OBJECT_NAME, fields=self.FIELDS, order_by=["id"]
        )
        current_by_id = self._normalize_rows(current_rows)

        create_values = [
            item
            for item_id, item in desired_by_id.items()
            if item_id not in current_by_id
        ]
        update_values = [
            item
            for item_id, item in desired_by_id.items()
            if item_id in current_by_id and current_by_id[item_id] != item
        ]
        delete_ids = [
            item_id for item_id in current_by_id if item_id not in desired_by_id
        ]

        if create_values:
            self._post(
                "create_objects.fcgi",
                {"object": self.OBJECT_NAME, "values": create_values},
            )

        if update_values:
            self._post(
                "modify_objects.fcgi",
                {"object": self.OBJECT_NAME, "values": update_values},
            )

        for delete_id in delete_ids:
            self._post(
                "destroy_objects.fcgi",
                {
                    "object": self.OBJECT_NAME,
                    "where": {self.OBJECT_NAME: {"id": delete_id}},
                },
            )

        return {
            "device_id": target_device.id,
            "device_name": target_device.name,
            "created": len(create_values),
            "updated": len(update_values),
            "deleted": len(delete_ids),
            "ok": True,
        }

    def sync_all_active_devices(self, target_devices: Iterable[Device] | None = None):
        desired_values = self._desired_values()
        targets = (
            list(target_devices)
            if target_devices is not None
            else list(Device.objects.filter(is_active=True).order_by("id"))
        )
        results = []
        for target_device in targets:
            try:
                results.append(
                    self.sync_target_device(
                        target_device, desired_values=desired_values
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Falha ao sincronizar registry de devices para %s",
                    target_device.name,
                )
                results.append(
                    {
                        "device_id": target_device.id,
                        "device_name": target_device.name,
                        "ok": False,
                        "error": str(exc),
                    }
                )
        return {
            "success": all(result.get("ok") for result in results) if results else True,
            "targets": len(targets),
            "registry_size": len(desired_values),
            "results": results,
        }
