# Anote aqui suas horas gastas refatorando essa bomba
#
# 4 Horas
# by: oPeraza
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Mapping, Optional, Union, overload

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from src.core.__seedwork__.infra.types.catraca_sync import (
    RemoteEnrollBioResponse,
    RemoteEnrollCardResponse,
)
from src.core.control_id.infra.control_id_django_app.models.device import Device

# ---------------------------------------------------------------------------
# Aliases de tipo
# ---------------------------------------------------------------------------

JsonDict = Dict[str, Any]
ObjectValues = List[Mapping[str, Any]]

# Campos obrigatórios por objeto na API da catraca.
# Centralizado aqui para facilitar manutenção sem tocar nos métodos.
REQUIRED_FIELDS_BY_OBJECT: Dict[str, List[str]] = {
    # Entidades com ID controlado pelo backend
    "users": ["id", "name"],
    "groups": ["id", "name"],
    "access_rules": ["id", "name", "type", "priority"],
    "time_zones": ["id", "name"],
    "time_spans": [
        "id",
        "time_zone_id",
        "start",
        "end",
        "sun",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "hol1",
        "hol2",
        "hol3",
    ],
    "areas": ["id", "name"],
    "portals": ["id", "name", "area_from_id", "area_to_id"],
    "templates": ["id", "user_id", "template"],
    "cards": ["id", "user_id", "value"],
    # Relações (pares únicos)
    "user_groups": ["user_id", "group_id"],
    "user_access_rules": ["user_id", "access_rule_id"],
    "portal_access_rules": ["portal_id", "access_rule_id"],
    "group_access_rules": ["group_id", "access_rule_id"],
    "access_rule_time_zones": ["access_rule_id", "time_zone_id"],
}

# Seções de nível raiz reconhecidas pela API de configuração da catraca.
_CONFIG_TOP_LEVEL_KEYS = frozenset(
    {"general", "monitor", "catra", "online_client", "push_server"}
)


# ---------------------------------------------------------------------------
# Exceção customizada
# ---------------------------------------------------------------------------


class CatracaSyncError(Exception):
    """
    Levantada quando uma operação de sincronização com a catraca falha.

    Carrega o ``status_code`` HTTP original (quando disponível) para que a
    camada superior possa decidir como responder sem precisar inspecionar a
    mensagem de texto.

    Exemplo de uso no ViewSet::

        with transaction.atomic():
            instance = serializer.save()          # banco
            self.create_in_catraca(instance)      # catraca — CatracaSyncError → rollback
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Dataclasses de configuração de dispositivo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)  # TORNAR IMUTÁVEL PARA EVITAR BUGS DE SESSÃO INVÁLIDA HELP
class DefaultDeviceClass:
    ip: str
    username: str
    password: str


@dataclass(frozen=True)
class DeviceClass:
    pk: int
    ip: str
    username: str
    password: str


# ---------------------------------------------------------------------------
# Helpers internos (funções puras, fora da classe)
# ---------------------------------------------------------------------------


def _normalize_config_value(value: Any) -> Any:
    """
    Normaliza recursivamente um valor para o formato esperado pela API da
    catraca (todas as folhas devem ser strings).
    """
    if isinstance(value, dict):
        return {k: _normalize_config_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_config_value(v) for v in value]
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    return str(value)


def _validate_object_fields(object_name: str, values: ObjectValues) -> None:
    """
    Valida se todos os campos obrigatórios estão presentes em *values*.

    Raises:
        CatracaSyncError: Se algum campo obrigatório estiver ausente.
    """
    required = REQUIRED_FIELDS_BY_OBJECT.get(object_name)
    if not required:
        return

    for idx, entry in enumerate(values):
        missing = [f for f in required if entry.get(f) in (None, "")]
        if missing:
            raise CatracaSyncError(
                f"Campos obrigatórios ausentes para '{object_name}' "
                f"(índice {idx}): {missing}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# Mixin principal
# ---------------------------------------------------------------------------


class ControlIDSyncMixin:
    """
    Mixin de comunicação com a API da catraca (ControlID).

    Responsabilidade única: HTTP confiável com a catraca.
    Controle de transação de banco é responsabilidade de quem chama.

    Em caso de falha de comunicação ou resposta inesperada da catraca,
    levanta ``CatracaSyncError`` para que a camada superior possa decidir
    como tratar (ex: rollback via ``transaction.atomic()`` no ViewSet).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.session: Optional[str] = None
        self._device: Optional[Device] = None
        self._use_default_config: bool = False

    # ------------------------------------------------------------------
    # Propriedades e configuração de dispositivo
    # ------------------------------------------------------------------

    @property
    def device(self) -> Union[DefaultDeviceClass, Device]:
        """Retorna o dispositivo atual ou o dispositivo padrão via settings."""
        if self._device is None and self._use_default_config:
            return DefaultDeviceClass(
                ip=settings.CATRAKA_URL,
                username=settings.CATRAKA_USER,
                password=settings.CATRAKA_PASS,
            )
        if self._device is None:
            raise CatracaSyncError("Device não definido")
        return self._device

    def set_device(self, device: Device) -> "ControlIDSyncMixin":
        """Define o dispositivo para usar nas operações e invalida a sessão atual."""
        self._device = device
        self._use_default_config = False
        self.session = None  # Força novo login
        return self

    # ------------------------------------------------------------------
    # Comunicação HTTP
    # ------------------------------------------------------------------

    def get_url(self, endpoint: str) -> str:
        """Constrói a URL completa para um endpoint da API."""
        ip = self.device.ip
        base_url = ip if ip.startswith(("http://", "https://")) else f"http://{ip}"
        return f"{base_url}/{endpoint}"

    def login(self, force_new: bool = False) -> str:
        """
        Realiza login na API da catraca com gerenciamento inteligente de sessão.

        Args:
            force_new: Força um novo login mesmo se já houver sessão ativa.

        Returns:
            Token de sessão.

        Raises:
            CatracaSyncError: Se o login falhar.
        """
        if self.session and not force_new:
            return self.session

        try:
            response = requests.post(
                self.get_url("login.fcgi"),
                json={"login": self.device.username, "password": self.device.password},
                timeout=10,
            )
            response.raise_for_status()
            self.session = response.json().get("session")
            return self.session  # type: ignore[return-value]
        except requests.RequestException as exc:
            self.session = None
            raise CatracaSyncError(
                f"Falha no login: {exc}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        json_data: Optional[JsonDict] = None,
        retry_on_auth_fail: bool = True,
        request_timeout: int = 10,
    ) -> requests.Response:
        """
        Executa um request HTTP com retry automático em caso de sessão expirada.

        Args:
            endpoint: Endpoint da API (ex: ``"set_configuration.fcgi"``).
            method: Método HTTP.
            json_data: Corpo JSON da requisição.
            retry_on_auth_fail: Tenta novamente com nova sessão em caso de 401.
            request_timeout: Timeout em segundos.

        Returns:
            Objeto ``requests.Response``.

        Raises:
            CatracaSyncError: Se a requisição falhar por erro de rede.
        """
        sess = self.login()
        request_kwargs: JsonDict = {
            "method": method,
            "url": self.get_url(f"{endpoint}?session={sess}"),
            "json": json_data,
            "headers": {"Content-Type": "application/json"},
            "timeout": request_timeout,
        }

        try:
            response = requests.request(**request_kwargs)

            if response.status_code == 401 and retry_on_auth_fail:
                sess = self.login(force_new=True)
                request_kwargs["url"] = self.get_url(f"{endpoint}?session={sess}")
                response = requests.request(**request_kwargs)

            return response

        except requests.RequestException as exc:
            raise CatracaSyncError(
                f"Erro na requisição para '{endpoint}': {exc}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

    @staticmethod
    def _extract_response_data(response: requests.Response) -> Any:
        """Extrai o corpo da resposta como JSON ou texto bruto."""
        if not response.text:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    # ------------------------------------------------------------------
    # Execução de endpoints remotos
    # ------------------------------------------------------------------

    def execute_remote_endpoint(
        self,
        endpoint: str,
        payload: Optional[JsonDict] = None,
        method: str = "POST",
        request_timeout: int = 10,
    ) -> requests.Response:
        """
        Executa um endpoint remoto na catraca atualmente selecionada.

        Raises:
            CatracaSyncError: Se a requisição falhar.
        """
        return self._make_request(
            endpoint=endpoint,
            method=method,
            json_data=payload,
            request_timeout=request_timeout,
        )

    def execute_remote_endpoint_in_devices(
        self,
        endpoint: str,
        payload: Optional[JsonDict],
        device_ids: List[int],
        method: str = "POST",
        request_timeout: int = 10,
    ) -> Response:
        """
        Executa o mesmo endpoint remoto em uma lista de catracas.

        Diferente dos demais métodos, este não levanta ``CatracaSyncError`` —
        erros por device são acumulados no campo ``results`` da resposta.
        """
        devices: List[Device] = list(
            Device.objects.filter(id__in=device_ids).order_by("id")
        )
        found_ids = {device.pk for device in devices}
        missing_ids = sorted(set(device_ids) - found_ids)

        if missing_ids:
            return Response(
                {"error": f"Devices não encontrados: {missing_ids}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not devices:
            return Response(
                {"error": "Nenhuma catraca encontrada para a operação"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results: List[JsonDict] = []
        success_count = 0

        for device in devices:
            self.set_device(device)
            try:
                raw = self.execute_remote_endpoint(
                    endpoint=endpoint,
                    payload=payload,
                    method=method,
                    request_timeout=request_timeout,
                )
                ok = 200 <= raw.status_code < 300
                results.append(
                    {
                        "device_id": device.pk,
                        "device_name": device.name,
                        "success": ok,
                        "status_code": raw.status_code,
                        "response": self._extract_response_data(raw),
                    }
                )
                if ok:
                    success_count += 1
            except CatracaSyncError as exc:
                results.append(
                    {
                        "device_id": device.pk,
                        "device_name": device.name,
                        "success": False,
                        "status_code": exc.status_code
                        or status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "error": str(exc),
                    }
                )

        failed_count = len(results) - success_count
        return Response(
            {
                "success": failed_count == 0,
                "endpoint": endpoint,
                "requested_devices": device_ids,
                "processed_devices": len(results),
                "successful_devices": success_count,
                "failed_devices": failed_count,
                "results": results,
            },
            status=status.HTTP_200_OK
            if failed_count == 0
            else status.HTTP_502_BAD_GATEWAY,
        )

    # ------------------------------------------------------------------
    # Utilitários de seleção de dispositivos
    # ------------------------------------------------------------------

    def _get_target_devices(
        self, device_ids: Optional[List[int]] = None
    ) -> List[Device]:
        """
        Resolve a lista de devices alvo com a seguinte prioridade:

        1. Se ``self._device`` estiver definido, usa apenas ele.
        2. Se ``device_ids`` for fornecido, filtra devices ativos por esses IDs.
        3. Caso contrário, retorna todos os devices ativos.
        """
        if self._device is not None:
            return [self._device]
        if device_ids:
            return list(Device.objects.filter(id__in=device_ids, is_active=True))
        return list(Device.objects.filter(is_active=True))

    # ------------------------------------------------------------------
    # CRUD de objetos na API da catraca
    # ------------------------------------------------------------------

    def load_objects(
        self,
        object_name: str,
        fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
    ) -> List[JsonDict]:
        """
        Carrega objetos da catraca.

        Args:
            object_name: Nome do objeto na API da catraca.
            fields: Campos a retornar (``None`` = todos).
            order_by: Campos de ordenação.

        Returns:
            Lista de objetos carregados.

        Raises:
            CatracaSyncError: Se a resposta não for 200.
        """
        payload: JsonDict = {"object": object_name}
        if fields:
            payload["fields"] = fields
        if order_by:
            payload["order_by"] = order_by

        response = self._make_request(
            "load_objects.fcgi", json_data=payload, request_timeout=30
        )

        if response.status_code != 200:
            raise CatracaSyncError(
                f"Falha ao carregar '{object_name}': {self._extract_response_data(response)}",
                status_code=response.status_code,
            )

        return response.json().get(object_name, [])

    def create_objects_in_all_devices(
        self,
        object_name: str,
        values: ObjectValues,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """
        Cria objetos em todas as catracas ativas (ou apenas nas indicadas por *device_ids*).

        Raises:
            CatracaSyncError: Propagada para a camada superior em caso de falha,
                permitindo rollback de transação Django via ``transaction.atomic()``.
        """
        devices = self._get_target_devices(device_ids)
        if not devices:
            return Response(
                {"error": "Nenhuma catraca ativa encontrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _validate_object_fields(object_name, values)

        first_response_data: Optional[JsonDict] = None

        for idx, device in enumerate(devices):
            self.set_device(device)
            response = self._make_request(
                "create_objects.fcgi",
                json_data={"object": object_name, "values": values},
                request_timeout=30,
            )
            if response.status_code != 200:
                raise CatracaSyncError(
                    f"Falha ao criar '{object_name}' no device '{device.name}': "
                    f"{self._extract_response_data(response)}",
                    status_code=response.status_code,
                )
            if idx == 0:
                try:
                    first_response_data = response.json()
                except Exception:
                    first_response_data = {"success": True}

        return Response(
            first_response_data or {"success": True},
            status=status.HTTP_201_CREATED,
        )

    def create_or_update_objects_in_all_devices(
        self,
        object_name: str,
        values: ObjectValues,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """
        Cria ou atualiza objetos em todas as catracas ativas.

        Raises:
            CatracaSyncError: Propagada para a camada superior em caso de falha.
        """
        devices = self._get_target_devices(device_ids)
        if not devices:
            return Response(
                {"error": "Nenhuma catraca ativa encontrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for device in devices:
            self.set_device(device)
            response = self._make_request(
                "create_or_modify_objects.fcgi",
                json_data={"object": object_name, "values": values},
                request_timeout=30,
            )
            if response.status_code != 200:
                raise CatracaSyncError(
                    f"Falha ao criar/atualizar '{object_name}' no device '{device.name}': "
                    f"{self._extract_response_data(response)}",
                    status_code=response.status_code,
                )

        return Response({"success": True}, status=status.HTTP_200_OK)

    def update_objects_in_all_devices(
        self,
        object_name: str,
        values: Mapping[str, Any],
        where: JsonDict,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """
        Atualiza objetos em todas as catracas ativas.

        Raises:
            CatracaSyncError: Propagada para a camada superior em caso de falha.
        """
        devices = self._get_target_devices(device_ids)
        if not devices:
            return Response(
                {"error": "Nenhuma catraca ativa encontrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for device in devices:
            self.set_device(device)
            response = self._make_request(
                "modify_objects.fcgi",
                json_data={"object": object_name, "values": values, "where": where},
                request_timeout=30,
            )
            if response.status_code != 200:
                raise CatracaSyncError(
                    f"Falha ao atualizar '{object_name}' no device '{device.name}': "
                    f"{self._extract_response_data(response)}",
                    status_code=response.status_code,
                )

        return Response({"success": True})

    def destroy_objects_in_all_devices(
        self,
        object_name: str,
        where: JsonDict,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """
        Remove objetos de todas as catracas ativas.

        Raises:
            CatracaSyncError: Propagada para a camada superior em caso de falha.
        """
        devices = self._get_target_devices(device_ids)
        if not devices:
            return Response(
                {"error": "Nenhuma catraca ativa encontrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for device in devices:
            self.set_device(device)
            response = self._make_request(
                "destroy_objects.fcgi",
                json_data={"object": object_name, "where": where},
                request_timeout=30,
            )
            # Alguns firmwares retornam 200 com JSON; outros 204 sem corpo.
            if response.status_code not in (200, 204):
                raise CatracaSyncError(
                    f"Falha ao remover '{object_name}' no device '{device.name}': "
                    f"{self._extract_response_data(response) or response.text}",
                    status_code=response.status_code,
                )

        return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Aliases de compatibilidade (delegates diretos)
    # ------------------------------------------------------------------

    def create_objects(
        self,
        object_name: str,
        values: ObjectValues,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """Alias de compatibilidade → :meth:`create_objects_in_all_devices`."""
        return self.create_objects_in_all_devices(
            object_name, values, device_ids=device_ids, **kwargs
        )

    def create_or_update_objects(
        self,
        object_name: str,
        values: ObjectValues,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """Alias de compatibilidade → :meth:`create_or_update_objects_in_all_devices`."""
        return self.create_or_update_objects_in_all_devices(
            object_name, values, device_ids=device_ids, **kwargs
        )

    def update_objects(
        self,
        object_name: str,
        values: Mapping[str, Any],
        where: JsonDict,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """Alias de compatibilidade → :meth:`update_objects_in_all_devices`."""
        return self.update_objects_in_all_devices(
            object_name, values, where, device_ids=device_ids, **kwargs
        )

    def destroy_objects(
        self,
        object_name: str,
        where: JsonDict,
        device_ids: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Response:
        """Alias de compatibilidade → :meth:`destroy_objects_in_all_devices`."""
        return self.destroy_objects_in_all_devices(
            object_name, where, device_ids=device_ids, **kwargs
        )

    # ------------------------------------------------------------------
    # Enroll remoto
    # ------------------------------------------------------------------

    @overload
    def remote_enroll(
        self, user_id: int, type: Literal["biometry"], save: bool, sync: bool
    ) -> RemoteEnrollBioResponse: ...

    @overload
    def remote_enroll(
        self, user_id: int, type: Literal["card"], save: bool, sync: bool
    ) -> RemoteEnrollCardResponse: ...

    def remote_enroll(
        self,
        user_id: int,
        type: str,
        save: bool,
        sync: bool,
    ) -> Union[RemoteEnrollBioResponse, RemoteEnrollCardResponse, Response]:
        """
        Realiza o cadastro remoto de um usuário na catraca.

        Args:
            user_id: ID do usuário.
            type: Tipo de cadastro (``"biometry"`` ou ``"card"``).
            save: Se deve persistir o cadastro na catraca.
            sync: Se deve sincronizar com o banco de dados.

        Returns:
            Dados do enroll ou ``Response`` de erro.

        Note:
            Este método não levanta ``CatracaSyncError`` pois o enroll é uma
            operação interativa — a resposta de erro já é suficientemente
            descritiva para o frontend tratar (ex: timeout do usuário).
        """
        if not self.device:
            return Response(
                {"error": "Nenhum dispositivo selecionado para cadastro"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload: JsonDict = {
            "user_id": user_id,
            "type": type,
            "save": save,
            "sync": sync,
        }

        try:
            sess = self.login()
            response = requests.post(
                self.get_url(f"remote_enroll.fcgi?session={sess}"),
                json=payload,
                timeout=40,  # Aguarda o usuário passar o dedo/cartão na catraca
            )

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_201_CREATED)

            return Response(
                {
                    "error": "Falha ao cadastrar na catraca",
                    "details": {
                        "status_code": response.status_code,
                        "content": response.text or "No content",
                    },
                },
                status=response.status_code,
            )

        except requests.Timeout:
            return Response(
                {
                    "error": "Tempo limite excedido",
                    "details": "O usuário demorou muito para realizar o cadastro.",
                },
                status=status.HTTP_408_REQUEST_TIMEOUT,
            )
        except CatracaSyncError as exc:
            return Response(
                {"error": "Erro ao processar cadastro", "details": str(exc)},
                status=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Configuração da catraca
    # ------------------------------------------------------------------

    def set_configuration(self, config: JsonDict) -> Response:
        """
        Aplica configurações em todas as catracas ativas.

        Os valores do dicionário são normalizados para string antes do envio,
        conforme esperado pela API da catraca.

        Args:
            config: Dicionário com as configurações a serem definidas.

        Raises:
            CatracaSyncError: Propagada para a camada superior em caso de falha.
        """
        devices = list(Device.objects.filter(is_active=True))
        if not devices:
            return Response(
                {"error": "Nenhuma catraca ativa encontrada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized = _normalize_config_value(config or {})
        # Envolve em {"general": ...} se nenhuma seção de nível raiz foi fornecida.
        final_payload: JsonDict = (
            normalized
            if any(k in normalized for k in _CONFIG_TOP_LEVEL_KEYS)
            else {"general": normalized}
        )

        for device in devices:
            self.set_device(device)
            response = self._make_request(
                "set_configuration.fcgi",
                json_data=final_payload,
                request_timeout=30,
            )
            if response.status_code != 200:
                raise CatracaSyncError(
                    f"Falha ao configurar device '{device.name}': "
                    f"{self._extract_response_data(response)}",
                    status_code=response.status_code,
                )

        return Response({"success": True})
