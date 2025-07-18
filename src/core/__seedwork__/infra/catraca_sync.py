from django.conf import settings
import requests
from typing import Dict, List, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

class ControlIDSyncMixin:
    """
    Mixin para sincronização com a catraca.
    Fornece funcionalidades básicas de comunicação com a API da catraca.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self._device = None
        self._use_default_config = settings.DEBUG

    @property
    def device(self):
        """Retorna o dispositivo atual ou busca o dispositivo padrão"""
        if self._device is None and self._use_default_config:
            # Usa configurações do settings.py como fallback
            return type('Device', (), {
                'ip': settings.CATRAKA_URL,
                'username': settings.CATRAKA_USER,
                'password': settings.CATRAKA_PASS
            })
        return self._device

    def set_device(self, device):
        """Define o dispositivo para usar nas operações"""
        self._device = device
        self._use_default_config = False
        self.session = None  # Força novo login
        return self

    def get_url(self, endpoint: str) -> str:
        """Constrói a URL para a API"""
        base_url = f"http://{self.device.ip}" if not self.device.ip.startswith(('http://', 'https://')) else self.device.ip
        return f"{base_url}/{endpoint}"

    def login(self) -> str:
        """
        Realiza login na API da catraca.
        Returns:
            str: Token de sessão
        """
        if self.session:
            return self.session

        if not self.device:
            raise ValueError("Nenhum dispositivo configurado e nenhum dispositivo padrão encontrado")

        response = requests.post(
            self.get_url("login.fcgi"), 
            json={
                "login": self.device.username,
                "password": self.device.password
            }
        )
        response.raise_for_status()
        self.session = response.json().get("session")
        return self.session

    def load_objects(self, object_name: str, fields: List[str] = None, order_by: List[str] = None) -> List[Dict[str, Any]]:
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
            self.get_url(f"load_objects.fcgi?session={sess}"),
            json=payload
        )
        if response.status_code != 200:
            raise Exception(response.json())
        response.raise_for_status()
        return response.json().get(f"{object_name}", [])

    def create_objects(self, object_name: str, values: List[Dict[str, Any]]) -> Response:
        """
        Cria objetos na catraca.
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para criar
        Returns:
            Response: Resposta da API
        """
        try:
            sess = self.login()
            response = requests.post(
                self.get_url(f"create_objects.fcgi?session={sess}"),
                json={"object": object_name, "values": values}
            )
            response.raise_for_status()
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_objects(self, object_name: str, values: Dict[str, Any], where: Dict[str, Any]) -> Response:
        """
        Atualiza objetos na catraca.
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para atualizar
            where: Condição para atualização
        Returns:
            Response: Resposta da API
        """
        try:
            sess = self.login()
            response = requests.post(
                self.get_url(f"modify_objects.fcgi?session={sess}"),
                json={
                    "object": object_name,
                    "values": values,
                    "where": where
                }
            )
            response.raise_for_status()
            return Response({"success": True})
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy_objects(self, object_name: str, where: Dict[str, Any]) -> Response:
        """
        Remove objetos da catraca.
        Args:
            object_name: Nome do objeto na API da catraca
            where: Condição para remoção
        Returns:
            Response: Resposta da API
        """
        try:
            sess = self.login()
            response = requests.post(
                self.get_url(f"destroy_objects.fcgi?session={sess}"),
                json={"object": object_name, "where": where}
            )
            response.raise_for_status()
            return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def remote_enroll(self, user_id: int, type: str, save: bool, sync: bool) -> Response:
        """
        Realiza o cadastro remoto de um usuário na catraca.
        Args:
            user_id: ID do usuário
            type: Tipo de cadastro (finger, face, etc.)
            save: Se deve salvar o cadastro
            sync: Se deve sincronizar com o banco de dados
        Returns:
            Response: Resposta da API
        """
        try:
            sess = self.login()
            
            # Payload com mais informações para debug
            payload = {
                "user_id": user_id,
                "type": type,
                "save": save,
                "sync": sync,
                "timeout": 30  # Aumenta o timeout para 30 segundos
            }
            
            # Faz a requisição com timeout explícito
            response = requests.post(
                self.get_url(f"remote_enroll.fcgi?session={sess}"),
                json=payload,
                timeout=30
            )
            
            # Verifica se a resposta é um JSON válido
            try:
                response_data = response.json()
            except ValueError:
                return Response(
                    {"error": "Resposta inválida da catraca", "details": response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verifica se houve erro específico da catraca
            if response.status_code != 200:
                return Response(
                    {"error": "Erro na catraca", "details": response_data},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            response.raise_for_status()
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except requests.Timeout:
            return Response(
                {"error": "Timeout ao tentar cadastrar biometria"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.RequestException as e:
            return Response(
                {"error": "Erro de comunicação com a catraca", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )