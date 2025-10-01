from rest_framework import status
from rest_framework.response import Response
from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin


class MonitorConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização de configurações de monitor com a catraca"""
    
    def update_monitor_config_in_catraca(self, instance):
        """Atualiza configurações de monitor na catraca"""
        try:
            # Monta o payload com os campos do monitor
            monitor_data = {}
            
            if hasattr(instance, 'request_timeout') and instance.request_timeout is not None:
                monitor_data['request_timeout'] = str(instance.request_timeout)
            if hasattr(instance, 'hostname') and instance.hostname:
                monitor_data['hostname'] = str(instance.hostname)
            if hasattr(instance, 'port') and instance.port is not None:
                monitor_data['port'] = str(instance.port)
            if hasattr(instance, 'path') and instance.path:
                monitor_data['path'] = str(instance.path)
            if hasattr(instance, 'inform_access_event_id') and instance.inform_access_event_id is not None:
                monitor_data['inform_access_event_id'] = "1" if instance.inform_access_event_id else "0"
            if hasattr(instance, 'alive_interval') and instance.alive_interval is not None:
                monitor_data['alive_interval'] = str(instance.alive_interval)
            
            if not monitor_data:
                return Response({
                    "success": False,
                    "error": "Nenhum campo de monitor para atualizar"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payload = {"monitor": monitor_data}
            
            # Usa o helper com retry automático de sessão
            response = self._make_request("set_configuration.fcgi", json_data=payload)
            
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": f"Erro ao atualizar configuração: {response.status_code}",
                    "details": response.text
                }, status=response.status_code)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Exceção ao atualizar configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_monitor_config_from_catraca(self):
        """Sincroniza configurações de monitor da catraca"""
        try:
            from ..models import MonitorConfig
            
            # Tenta diferentes payloads para obter o bloco monitor
            payloads = [
                {"monitor": {}},
                {"monitor": {"fields": ["request_timeout", "hostname", "port", "path", "inform_access_event_id", "alive_interval"]}},
            ]
            
            for payload in payloads:
                response = self._make_request("get_configuration.fcgi", json_data=payload)
                
                if response.status_code != 200:
                    continue
                
                data = response.json() or {}
                monitor_data = data.get("monitor", {})
                
                if isinstance(monitor_data, dict) and monitor_data:
                    # Sucesso - retorna os dados
                    return Response({
                        "success": True,
                        "monitor": monitor_data
                    }, status=status.HTTP_200_OK)
            
            # Nenhum payload funcionou
            return Response({
                "success": False,
                "error": "Dispositivo não retornou configurações de monitor"
            }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Erro ao sincronizar configurações: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
