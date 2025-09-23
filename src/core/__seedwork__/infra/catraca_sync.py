from django.conf import settings
import requests
from typing import Dict, List, Any, Optional
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction

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

    def create_objects_in_all_devices(self, object_name: str, values: List[Dict[str, Any]]) -> Response:
        """
        Cria objetos em todas as catracas ativas.
        Args:
            object_name: Nome do objeto na API da catraca
            values: Lista de valores para criar
        Returns:
            Response: Resposta da API
        """
        try:
            from src.core.control_Id.infra.control_id_django_app.models.device import Device
            
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response({"error": "Nenhuma catraca ativa encontrada"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validação de campos obrigatórios para garantir IDs consistentes entre backend e catracas
            required_fields_by_object = {
                # Entidades com ID controlado pelo backend
                "users": ["id", "name"],
                "groups": ["id", "name"],
                "access_rules": ["id", "name", "type", "priority"],
                "time_zones": ["id", "name"],
                "time_spans": ["id", "time_zone_id", "start", "end", "sun", "mon", "tue", "wed", "thu", "fri", "sat", "hol1", "hol2", "hol3"],
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
                        return Response({
                            "error": f"Campos obrigatórios ausentes para {object_name}",
                            "index": idx,
                            "missing": missing,
                        }, status=status.HTTP_400_BAD_REQUEST)

            first_response_data = None
            with transaction.atomic():
                for idx, device in enumerate(devices):
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"create_objects.fcgi?session={sess}"),
                        json={"object": object_name, "values": values}
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()
                    if idx == 0:
                        try:
                            first_response_data = response.json()
                        except Exception:
                            first_response_data = {"success": True}
                
                return Response(first_response_data or {"success": True}, status=status.HTTP_201_CREATED)
                
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_objects_in_all_devices(self, object_name: str, values: Dict[str, Any], where: Dict[str, Any]) -> Response:
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
            from src.core.control_Id.infra.control_id_django_app.models.device import Device
            
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response({"error": "Nenhuma catraca ativa encontrada"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"modify_objects.fcgi?session={sess}"),
                        json={
                            "object": object_name,
                            "values": values,
                            "where": where
                        }
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()
                
                return Response({"success": True})
                
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy_objects_in_all_devices(self, object_name: str, where: Dict[str, Any]) -> Response:
        """
        Remove objetos de todas as catracas ativas.
        Args:
            object_name: Nome do objeto na API da catraca
            where: Condição para remoção
        Returns:
            Response: Resposta da API
        """
        try:
            from src.core.control_Id.infra.control_id_django_app.models.device import Device
            
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response({"error": "Nenhuma catraca ativa encontrada"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                for device in devices:
                    self.set_device(device)
                    sess = self.login()
                    response = requests.post(
                        self.get_url(f"destroy_objects.fcgi?session={sess}"),
                        json={"object": object_name, "where": where}
                    )
                    if response.status_code != 200:
                        raise Exception(response.json())
                    response.raise_for_status()
                
                return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)
                
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def create_objects(self, object_name: str, values: List[Dict[str, Any]]) -> Response:
        """Mantido por compatibilidade, chama create_objects_in_all_devices"""
        return self.create_objects_in_all_devices(object_name, values)

    def update_objects(self, object_name: str, values: Dict[str, Any], where: Dict[str, Any]) -> Response:
        """Mantido por compatibilidade, chama update_objects_in_all_devices"""
        return self.update_objects_in_all_devices(object_name, values, where)

    def destroy_objects(self, object_name: str, where: Dict[str, Any]) -> Response:
        """Mantido por compatibilidade, chama destroy_objects_in_all_devices"""
        return self.destroy_objects_in_all_devices(object_name, where)

    def remote_enroll(self, user_id: int, type: str, save: bool, sync: bool) -> Response:
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
            from src.core.control_Id.infra.control_id_django_app.models.device import Device
            
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response({"error": "Nenhuma catraca ativa encontrada"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Payload com mais informações para debug
            payload = {
                "user_id": user_id,
                "type": type,
                "save": save,
                "sync": sync,
                "timeout": 40
            }
            
            # Tenta em cada catraca até uma funcionar
            last_error = None
            for device in devices:
                try:
                    self.set_device(device)
                    sess = self.login()
                    
                    response = requests.post(
                        self.get_url(f"remote_enroll.fcgi?session={sess}"),
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        return Response(response_data, status=status.HTTP_201_CREATED)
                        
                    last_error = {
                        "status_code": response.status_code,
                        "content": response.text if response.text else "No content"
                    }
                except Exception as e:
                    last_error = {
                        "error": str(e)
                    }
                    continue
            
            return Response({
                "error": "Falha ao cadastrar em todas as catracas",
                "details": last_error
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            return Response({
                "error": "Erro ao processar cadastro",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)