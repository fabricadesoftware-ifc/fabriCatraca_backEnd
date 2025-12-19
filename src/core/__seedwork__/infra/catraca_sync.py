from typing import Any, Dict, List

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response


class ControlIDSyncMixin:
    """
    Mixin para sincronização com a catraca.
    Fornece funcionalidades básicas de comunicação com a API da catraca.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self._device = None
        self._use_default_config = False

    @property
    def device(self):
        """Retorna o dispositivo atual ou busca o dispositivo padrão"""
        if self._device is None and self._use_default_config:
            # Usa configurações do settings.py como fallback
            return type(
                "Device",
                (),
                {
                    "ip": settings.CATRAKA_URL,
                    "username": settings.CATRAKA_USER,
                    "password": settings.CATRAKA_PASS,
                },
            )
        return self._device

    def set_device(self, device):
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
        json_data: Dict = None,
        retry_on_auth_fail: bool = True,
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
                timeout=10,
            )

            if response.status_code == 401 and retry_on_auth_fail:
                sess = self.login(force_new=True)
                url = self.get_url(f"{endpoint}?session={sess}")
                response = requests.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

            return response

        except requests.RequestException as e:
            # trunk-ignore(ruff/B904)
            raise Exception(f"Erro na requisição para {endpoint}: {str(e)}")

    def load_objects(
        self, object_name: str, fields: List[str] = None, order_by: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Carrega objetos da catraca.
        Args:
            object_name: Nome do objeto na API da catraca
            fields: Lista de campos para retornar
            order_by: Lista de campos para ordenação
        Returns:
            List[Dict[str, Any]]: Lista de objetos carregados
        """
        sess = self.login()
        payload = {"object": object_name}

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

    def create_objects_in_all_devices(
        self, object_name: str, values: List[Dict[str, Any]]
    ) -> Response:
        """
        Cria objetos em todas as catracas ativas.
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para criar
        Returns:
            Response: Resposta da API
        """
        try:
            from src.core.control_Id.infra.control_id_django_app.models.device import (
                Device,
            )

            # Se um device foi definido via self.set_device, aplica somente nele
            if self._device is not None:
                devices = [self._device]
            else:
                devices = list(Device.objects.filter(is_active=True))
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

    def update_objects_in_all_devices(
        self, object_name: str, values: Dict[str, Any], where: Dict[str, Any]
    ) -> Response:
        """
        Atualiza objetos em todas as catracas ativas.
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para atualizar
            where: Condição para atualização
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
        self, object_name: str, where: Dict[str, Any]
    ) -> Response:
        """
        Remove objetos de todas as catracas ativas.
        Args:
            object_name: Nome do objeto na API da catraca
            where: Condição para remoção
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

            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"destroy_objects.fcgi?session={sess}"),
                        json={"object": object_name, "where": where},
                        timeout=30,
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()

                return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)

        except requests.RequestException as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_objects(
        self, object_name: str, values: List[Dict[str, Any]]
    ) -> Response:
        """Mantido por compatibilidade, chama create_objects_in_all_devices"""
        return self.create_objects_in_all_devices(object_name, values)

    def update_objects(
        self, object_name: str, values: Dict[str, Any], where: Dict[str, Any]
    ) -> Response:
        """Mantido por compatibilidade, chama update_objects_in_all_devices"""
        return self.update_objects_in_all_devices(object_name, values, where)

    def destroy_objects(self, object_name: str, where: Dict[str, Any]) -> Response:
        """Mantido por compatibilidade, chama destroy_objects_in_all_devices"""
        return self.destroy_objects_in_all_devices(object_name, where)

    def remote_enroll(
        self, user_id: int, type: str, save: bool, sync: bool
    ) -> Response:
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
                "timeout": device_timeout,
            }

            sess = self.login()

            # Timeout do request um pouco maior que o da catraca (35s)
            request_timeout = device_timeout + 5

            response = requests.post(
                self.get_url(f"remote_enroll.fcgi?session={sess}"),
                json=payload,
                timeout=request_timeout,
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
