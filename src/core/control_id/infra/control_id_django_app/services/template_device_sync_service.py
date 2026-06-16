from __future__ import annotations

from typing import Any

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.models.template import Template
from src.core.user.infra.user_django_app.models import User


class TemplateDeviceSyncError(RuntimeError):
    pass


class TemplateDeviceSyncService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    @staticmethod
    def to_payload(template: Template) -> dict[str, Any]:
        return {
            "id": template.id,
            "user_id": template.user_id,
            "template": template.template,
            "finger_type": template.finger_type,
            "finger_position": template.finger_position,
        }

    def get_target_devices_for_user(self, user: User) -> list[Device]:
        return list(user.get_target_devices(include_inactive=False))

    def create_template_in_device(self, device: Device, template: Template) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.create_objects(
                "templates",
                [self.to_payload(template)],
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise TemplateDeviceSyncError(
                f"Erro ao criar biometria na catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_201_CREATED:
            raise TemplateDeviceSyncError(
                f"Erro ao criar biometria na catraca {device.name}: {response.data}"
            )

    def replicate_template_to_user_devices(self, template: Template) -> list[dict]:
        errors = []

        for device in self.get_target_devices_for_user(template.user):
            try:
                self.create_template_in_device(device, template)
            except TemplateDeviceSyncError as exc:
                errors.append(
                    {
                        "device_id": device.pk,
                        "device_name": device.name,
                        "details": str(exc),
                    }
                )

        return errors

    def update_template_in_device(self, device: Device, template: Template) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.update_objects(
                "templates",
                self.to_payload(template),
                {"templates": {"id": template.id}},
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise TemplateDeviceSyncError(
                f"Erro ao atualizar biometria na catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_200_OK:
            raise TemplateDeviceSyncError(
                f"Erro ao atualizar biometria na catraca {device.name}: {response.data}"
            )

    def update_template_for_user_devices(self, template: Template) -> None:
        for device in self.get_target_devices_for_user(template.user):
            self.update_template_in_device(device, template)

    def delete_template_from_device(self, device: Device, template: Template) -> None:
        self.gateway.set_device(device)
        try:
            response = self.gateway.destroy_objects(
                "templates",
                {"templates": {"id": template.id}},
                device_ids=[device.id],
            )
        except CatracaSyncError as exc:
            raise TemplateDeviceSyncError(
                f"Erro ao deletar biometria da catraca {device.name}: {exc}"
            ) from exc

        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise TemplateDeviceSyncError(
                f"Erro ao deletar biometria da catraca {device.name}: {response.data}"
            )

    def delete_template_for_user_devices(self, template: Template) -> None:
        for device in self.get_target_devices_for_user(template.user):
            self.delete_template_from_device(device, template)
