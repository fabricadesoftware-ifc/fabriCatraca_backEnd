from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import requests
from rest_framework.response import Response

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_id.infra.control_id_django_app.models.device import Device

JsonObject = dict[str, Any]
ObjectValues = Sequence[Mapping[str, Any]]


class ControlIDGateway:
    """Adapter explicito para a API da ControlID.

    Por enquanto ele delega para o sync legado. A diferenca importante e que
    o dominio de usuario passa a depender deste contrato pequeno, nao do mixin
    HTTP inteiro.
    """

    def __init__(self, client: ControlIDSyncMixin | None = None) -> None:
        self._client = client or ControlIDSyncMixin()

    @property
    def client(self) -> ControlIDSyncMixin:
        return self._client

    def set_device(self, device: Device) -> None:
        self._client.set_device(device)

    def load_objects(self, object_name: str, **kwargs: Any) -> list[JsonObject]:
        return self._client.load_objects(object_name, **kwargs)

    def create_objects(
        self,
        object_name: str,
        values: ObjectValues,
        **kwargs: Any,
    ) -> Response:
        return self._client.create_objects(object_name, values, **kwargs)

    def create_or_update_objects(
        self,
        object_name: str,
        values: ObjectValues,
        **kwargs: Any,
    ) -> Response:
        return self._client.create_or_update_objects(object_name, values, **kwargs)

    def update_objects(
        self,
        object_name: str,
        values: Mapping[str, Any],
        where: JsonObject,
        **kwargs: Any,
    ) -> Response:
        return self._client.update_objects(object_name, values, where, **kwargs)

    def destroy_objects(
        self,
        object_name: str,
        where: JsonObject,
        **kwargs: Any,
    ) -> Response:
        return self._client.destroy_objects(object_name, where, **kwargs)

    def remote_enroll(
        self,
        *,
        user_id: int,
        enrollment_type: str,
        save: bool,
        sync: bool,
    ) -> Response:
        return self._client.remote_enroll(
            user_id=user_id,
            type=enrollment_type,
            save=save,
            sync=sync,
        )

    def extract_template(
        self,
        device: Device,
        raw_image: bytes,
        *,
        width: int = 256,
        height: int = 288,
        timeout: int = 40,
    ) -> JsonObject:
        """Extrai um template biometrico a partir da imagem bruta do leitor."""
        self.set_device(device)
        session = self._client.login()
        response = requests.post(
            self._client.get_url(f"template_extract.fcgi?session={session}"),
            params={"width": width, "height": height},
            data=raw_image,
            headers={"Content-Type": "application/octet-stream"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Resposta invalida da catraca ao extrair template.")
        return payload
