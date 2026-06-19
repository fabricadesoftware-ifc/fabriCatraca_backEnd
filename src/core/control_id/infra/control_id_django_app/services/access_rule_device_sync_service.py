from __future__ import annotations

from typing import Any

from rest_framework import status

from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models import AccessRule


class AccessRuleDeviceSyncError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class AccessRuleDeviceSyncService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    @staticmethod
    def to_payload(access_rule: AccessRule) -> dict[str, int | str]:
        return {
            "id": access_rule.id,
            "name": access_rule.name,
            "type": access_rule.type,
            "priority": access_rule.priority,
        }

    def _raise_sync_error(
        self,
        message: str,
        *,
        response=None,
        exc: CatracaSyncError | None = None,
    ) -> None:
        if exc is not None:
            raise AccessRuleDeviceSyncError(
                message,
                status_code=exc.status_code or status.HTTP_400_BAD_REQUEST,
                details=str(exc),
            ) from exc

        raise AccessRuleDeviceSyncError(
            message,
            status_code=getattr(response, "status_code", status.HTTP_400_BAD_REQUEST),
            details=getattr(response, "data", None),
        )

    def create(self, access_rule: AccessRule) -> None:
        try:
            response = self.gateway.create_objects(
                "access_rules",
                [self.to_payload(access_rule)],
            )
        except CatracaSyncError as exc:
            self._raise_sync_error("Erro ao criar regra de acesso na catraca.", exc=exc)

        if response.status_code != status.HTTP_201_CREATED:
            self._raise_sync_error(
                "Erro ao criar regra de acesso na catraca.",
                response=response,
            )

    def update(self, access_rule: AccessRule) -> None:
        try:
            response = self.gateway.update_objects(
                "access_rules",
                self.to_payload(access_rule),
                {"access_rules": {"id": access_rule.id}},
            )
        except CatracaSyncError as exc:
            self._raise_sync_error(
                "Erro ao atualizar regra de acesso na catraca.",
                exc=exc,
            )

        if response.status_code != status.HTTP_200_OK:
            self._raise_sync_error(
                "Erro ao atualizar regra de acesso na catraca.",
                response=response,
            )

    def delete(self, access_rule: AccessRule) -> None:
        try:
            response = self.gateway.destroy_objects(
                "access_rules",
                {"access_rules": {"id": access_rule.id}},
            )
        except CatracaSyncError as exc:
            self._raise_sync_error(
                "Erro ao remover regra de acesso da catraca.",
                exc=exc,
            )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            self._raise_sync_error(
                "Erro ao remover regra de acesso da catraca.",
                response=response,
            )
