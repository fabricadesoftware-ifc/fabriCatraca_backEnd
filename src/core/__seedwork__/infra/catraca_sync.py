from typing import Any, Dict, List, Mapping, overload, Literal, Union
from dataclasses import dataclass
from typing import Optional
from src.core.control_Id.infra.control_id_django_app.models.device import Device

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from src.core.__seedwork__.infra.types.catraca_sync import RemoteEnrollBioResponse, RemoteEnrollCardResponse

@dataclass
class DefaultDeviceClass:
    ip: str
    username: str
    password: str

@dataclass
class DeviceClass:
    pk: int
    ip: str
    username: str
    password: str


class ControlIDSyncMixin:
    """
    Mixin para sincronização com a catraca.
    Fornece funcionalidades básicas de comunicação com a API da catraca.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self._device: Optional[Device] = None
        self._use_default_config = False

    @property
    def device(self) -> DefaultDeviceClass | Device:
        """Retorna o dispositivo atual ou busca o dispositivo padrão"""
        if self._device is None and self._use_default_config:
            # Usa configurações do settings.py como fallback
            return DefaultDeviceClass(
                ip=settings.CATRAKA_URL,
                username=settings.CATRAKA_USER,
                password=settings.CATRAKA_PASS,
            )

        if self._device is None:
            raise ValueError("Device não definido")


        return self._device

    def set_device(self, device: Device):
        """Define o dispositivo para usar nas operações"""
        self._device = device
        self._use_default_config = False
        self.session = None  # Força novo login
        return self

    def get_url(self, endpoint: str) -> str:
        """Constrói a URL para a API"""
        base_url = (
            f"http://{self.device.ip}"
            if not self.device.ip.startswith(("http://", "https://"))
            else self.device.ip
        )
        return f"{base_url}/{endpoint}"

    def login(self, force_new: bool = False) -> str:
        """
        Realiza login na API da catraca com gerenciamento inteligente de sessão.
        Args:
            force_new: Força um novo login mesmo se já houver sessão
        Returns:
            str: Token de sessão
        """
        # Se já tem sessão válida e não está forçando novo login, reutiliza
        if self.session and not force_new:
            return self.session

        if not self.device:
            raise ValueError(
                "Nenhum dispositivo configurado e nenhum dispositivo padrão encontrado"
            )

        try:
            response = requests.post(
                self.get_url("login.fcgi"),
                json={"login": self.device.username, "password": self.device.password},
                timeout=10,
            )
            response.raise_for_status()
            self.session = response.json().get("session")
            return self.session
        except requests.RequestException as e:
            self.session = None  # Limpa sessão inválida
            # trunk-ignore(ruff/B904)
            raise Exception(f"Falha no login: {str(e)}")

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        json_data: Optional[Dict[str, Any]] = None,
        retry_on_auth_fail: bool = True,
        request_timeout: int = 10,
    ) -> requests.Response:
        """
        Helper para fazer requests com retry automático em caso de sessão expirada.
        Args:
            endpoint: Endpoint da API (ex: "set_configuration.fcgi")
            method: Método HTTP (POST, GET, etc)
            json_data: Dados JSON para enviar
            retry_on_auth_fail: Se deve tentar novamente com novo login em caso de erro de autenticação
        Returns:
            requests.Response: Resposta da API
        """
        sess = self.login()
        url = self.get_url(f"{endpoint}?session={sess}")

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                headers={"Content-Type": "application/json"},
                timeout=request_timeout,
            )

            if response.status_code == 401 and retry_on_auth_fail:
                sess = self.login(force_new=True)
                url = self.get_url(f"{endpoint}?session={sess}")
                response = requests.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers={"Content-Type": "application/json"},
                    timeout=request_timeout,
                )

            return response

        except requests.RequestException as e:
            raise Exception(f"Erro na requisição para {endpoint}: {str(e)}")

    @staticmethod
    def _extract_response_data(response: requests.Response) -> Any:
        if not response.text:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text

    def execute_remote_endpoint(
        self,
        endpoint: str,
        payload: Dict[str, Any] | None = None,
        method: str = "POST",
        request_timeout: int = 10,
    ) -> requests.Response:
        """
        Executa um endpoint remoto na catraca atuallmente selecionada.
        """
        if not self.device:
            raise ValueError("Nenhum dispositivo selecionado")

        return self._make_request(
            endpoint=endpoint,
            method=method,
            json_data=payload,
            request_timeout=request_timeout,
        )

    def execute_remote_endpoint_in_devices(
        self,
        endpoint: str,
        payload: Dict[str, Any] | None,
        device_ids: List[int],
        method: str = "POST",
        request_timeout: int = 10,
    ) -> Response:
        """
        Executa o mesmo endpoint remoto em uma lista de catracas.
        """
        try:

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

            results = []
            success_count = 0

            for device in devices:
                self.set_device(device)

                try:
                    response = self.execute_remote_endpoint(
                        endpoint=endpoint,
                        payload=payload,
                        method=method,
                        request_timeout=request_timeout,
                    )
                    response_data = self._extract_response_data(response)
                    ok = 200 <= response.status_code < 300

                    results.append(
                        {
                            "device_id": device.pk,
                            "device_name": device.name,
                            "success": ok,
                            "status_code": response.status_code,
                            "response": response_data,
                        }
                    )

                    if ok:
                        success_count += 1
                except Exception as exc:
                    results.append(
                        {
                            "device_id": device.pk,
                            "device_name": device.name,
                            "success": False,
                            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "error": str(exc),
                        }
                    )

            failed_count = len(results) - success_count
            response_status = (
                status.HTTP_200_OK
                if failed_count == 0
                else status.HTTP_502_BAD_GATEWAY
            )

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
                status=response_status,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def load_objects(
        self,
        object_name: str,
        fields: list[str] | None = None,
        order_by: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Carrega objetos da catraca.
        Args:
            object_name: Nome do objeto na API da catraca
            fields: Lista de campos para retornar
            order_by: Lista de campos para ordenação
        Returns:
            list[dict[str, Any]]: Lista de objetos carregados
        """
        sess = self.login()
        payload: dict[str, Any] = {"object": object_name}

        if fields:
            payload["fields"] = fields
        if order_by:
            payload["order_by"] = order_by

        response = requests.post(
            self.get_url(f"load_objects.fcgi?session={sess}"), json=payload, timeout=30
        )
        if response.status_code != 200:
            raise Exception(response.json())
        response.raise_for_status()
        return response.json().get(f"{object_name}", [])

    def _get_target_devices(
        self, device_ids: List[int] | None = None
    ) -> list:
        """
        Retorna a lista de devices alvo.
        Se device_ids for fornecido, filtra por esses IDs.
        Se self._device estiver definido, usa apenas aquele device.
        Caso contrário, retorna todos os devices ativos.
        """
        from src.core.control_Id.infra.control_id_django_app.models.device import (
            Device,
        )

        if self._device is not None:
            return [self._device]
        if device_ids:
            return list(Device.objects.filter(id__in=device_ids, is_active=True))
        return list(Device.objects.filter(is_active=True))

    def create_objects_in_all_devices(
        self, object_name: str, values: List[Mapping[str, Any]], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """
        Cria objetos em todas as catracas ativas (ou apenas nas especificadas por device_ids).
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para criar
            device_ids: Lista opcional de device IDs para limitar o escopo
        Returns:
            Response: Resposta da API
        """
        try:
            devices = self._get_target_devices(device_ids)

            if not devices:
                return Response(
                    {"error": "Nenhuma catraca ativa encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validação de campos obrigatórios para garantir IDs consistentes entre backend e catracas
            required_fields_by_object = {
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

            if object_name in required_fields_by_object:
                req_fields = required_fields_by_object[object_name]
                for idx, v in enumerate(values):
                    missing = [f for f in req_fields if v.get(f) in (None, "")]
                    if missing:
                        return Response(
                            {
                                "error": f"Campos obrigatórios ausentes para {object_name}",
                                "index": idx,
                                "missing": missing,
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            first_response_data = None
            with transaction.atomic():
                for idx, device in enumerate(devices):
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"create_objects.fcgi?session={sess}"),
                        json={"object": object_name, "values": values},
                        timeout=30,
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()
                    if idx == 0:
                        try:
                            first_response_data = response.json()
                        except Exception:
                            first_response_data = {"success": True}

                return Response(
                    first_response_data or {"success": True},
                    status=status.HTTP_201_CREATED,
                )

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def create_or_update_objects_in_all_devices(
        self, object_name: str, values: List[Mapping[str, Any]], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """
        Cria ou atualiza objetos em todas as catracas ativas (ou apenas nas especificadas por device_ids).
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para criar ou atualizar
            device_ids: Lista opcional de device IDs para limitar o escopo
        Returns:
            Response: Resposta da API
        """
        try:
            devices = self._get_target_devices(device_ids)
            if not devices:
                return Response(
                    {"error": "Nenhuma catraca ativa encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"create_or_modify_objects.fcgi?session={sess}"),
                        json={"object": object_name, "values": values},
                        timeout=30,
                    )
                    if response.status_code != 200:
                        try:
                            error_data = response.json()
                        except Exception:
                            error_data = {"error": response.text}
                        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
                    response.raise_for_status()

                return Response({"success": True}, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_objects_in_all_devices(
        self, object_name: str, values: Mapping[str, Any], where: Dict[str, Any], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """
        Atualiza objetos em todas as catracas ativas (ou apenas nas especificadas por device_ids).
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para atualizar
            where: Condição para atualização
            device_ids: Lista opcional de device IDs para limitar o escopo
        Returns:
            Response: Resposta da API
        """
        try:
            devices = self._get_target_devices(device_ids)
            if not devices:
                return Response(
                    {"error": "Nenhuma catraca ativa encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"modify_objects.fcgi?session={sess}"),
                        json={"object": object_name, "values": values, "where": where},
                        timeout=30,
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()

                return Response({"success": True})

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy_objects_in_all_devices(
        self, object_name: str, where: Dict[str, Any], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """
        Remove objetos de todas as catracas ativas (ou apenas nas especificadas por device_ids).
        Args:
            object_name: Nome do objeto na API da catraca
            where: Condição para remoção
            device_ids: Lista opcional de device IDs para limitar o escopo
        Returns:
            Response: Resposta da API
        """
        try:
            devices = self._get_target_devices(device_ids)
            if not devices:
                return Response(
                    {"error": "Nenhuma catraca ativa encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"destroy_objects.fcgi?session={sess}"),
                        json={"object": object_name, "where": where},
                        timeout=30,
                    )
                    # Alguns firmwares retornam 200 com JSON; outros 204 sem corpo.
                    if response.status_code not in (200, 204):
                        raise Exception(response.json() if response.content else response.text)

                return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_objects(
        self, object_name: str, values: List[Mapping[str, Any]], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """Mantido por compatibilidade, chama create_objects_in_all_devices"""
        return self.create_objects_in_all_devices(object_name, values, device_ids=device_ids, **kwargs)

    def create_or_update_objects(
        self, object_name: str, values: List[Mapping[str, Any]], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """Mantido por compatibilidade, chama create_or_update_objects_in_all_devices"""
        return self.create_or_update_objects_in_all_devices(object_name, values, device_ids=device_ids, **kwargs)

    def update_objects(
        self, object_name: str, values: Mapping[str, Any], where: Dict[str, Any], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """Mantido por compatibilidade, chama update_objects_in_all_devices"""
        return self.update_objects_in_all_devices(object_name, values, where, device_ids=device_ids, **kwargs)

    def destroy_objects(
        self, object_name: str, where: Dict[str, Any], device_ids: List[int] | None = None, **kwargs
    ) -> Response:
        """Mantido por compatibilidade, chama destroy_objects_in_all_devices"""
        return self.destroy_objects_in_all_devices(object_name, where, device_ids=device_ids, **kwargs)

    @overload
    def remote_enroll(
        self, user_id: int, type: Literal["biometry"], save: bool, sync: bool
    ) -> RemoteEnrollBioResponse: ...

    @overload
    def remote_enroll(
        self, user_id: int, type: Literal["card"], save: bool, sync: bool
    ) -> RemoteEnrollCardResponse: ...

    def remote_enroll(
        self, user_id: int, type: str, save: bool, sync: bool
    ) -> Union[RemoteEnrollBioResponse, RemoteEnrollCardResponse] | Response:
        """
        Realiza o cadastro remoto de um usuário na catraca.
        Args:
            user_id: ID do usuário
            type: Tipo de cadastro (biometric, face, etc.)
            save: Se deve salvar o cadastro
            sync: Se deve sincronizar com o banco de dados
        Returns:
            Response: Resposta da API
        """
        try:
            if not self.device:
                return Response(
                    {"error": "Nenhum dispositivo selecionado para cadastro"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Timeout da catraca (30s)
            device_timeout = 30

            # Payload
            payload = {
                "user_id": user_id,
                "type": type,
                "save": save,
                "sync": sync,
            }

            sess = self.login()

            # Timeout do request um pouco maior que o da catraca (35s)

            response = requests.post(
                self.get_url(f"remote_enroll.fcgi?session={sess}"),
                json=payload,
                timeout=device_timeout,
            )

            if response.status_code == 200:
                response_data = response.json()
                return Response(response_data, status=status.HTTP_201_CREATED)

            return Response(
                {
                    "error": "Falha ao cadastrar na catraca",
                    "details": {
                        "status_code": response.status_code,
                        "content": response.text if response.text else "No content",
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

        except Exception as e:
            return Response(
                {"error": "Erro ao processar cadastro", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def set_configuration(self, config: Dict[str, Any]) -> Response:
        """
        Define configurações na catraca.
        Args:
            config: Dicionário com as configurações a serem definidas
        Returns:
            Response: Resposta da API
        """
        try:
            from src.core.control_Id.infra.control_id_django_app.models.device import (
                Device,
            )

            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response(
                    {"error": "Nenhuma catraca ativa encontrada"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Normaliza payload: API espera strings. Converte bool -> "1"/"0", números -> str, None -> ""
            def normalize_values(value: Any) -> Any:
                if isinstance(value, dict):
                    return {k: normalize_values(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [normalize_values(v) for v in value]
                if isinstance(value, str):
                    return value  # Já é string, não modifica
                if isinstance(value, bool):
                    return "1" if value else "0"
                if value is None:
                    return ""
                if isinstance(value, (int, float)):
                    return str(value)
                return str(value)

            normalized_config = normalize_values(config or {})

            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()

                    # Determina o payload final
                    final_payload = (
                        normalized_config
                        if any(
                            key in normalized_config
                            for key in (
                                "general",
                                "monitor",
                                "catra",
                                "online_client",
                                "push_server",
                            )
                        )
                        else {"general": normalized_config}
                    )

                    response = requests.post(
                        self.get_url(f"set_configuration.fcgi?session={sess}"),
                        json=final_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30,
                    )

                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()

                return Response({"success": True})

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
