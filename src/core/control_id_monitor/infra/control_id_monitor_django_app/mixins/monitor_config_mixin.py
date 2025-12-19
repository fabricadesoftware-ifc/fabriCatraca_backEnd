from rest_framework import status
from rest_framework.response import Response
from src.core.__seedwork__.infra.catraca_sync import ControlIDSyncMixin


class MonitorConfigSyncMixin(ControlIDSyncMixin):
    """
    Mixin para sincronização de configurações de Monitor com a catraca
    
    O Monitor é um sistema PUSH onde a CATRACA envia logs automaticamente
    para um servidor configurado, ao invés de termos que ficar sincronizando.
    
    Isso é muito mais eficiente porque:
    - Logs chegam em tempo real quando alguém passa
    - Não precisa ficar fazendo polling/sync periódico
    - Reduz carga no servidor e na catraca
    - Permite notificações instantâneas
    """
    
    def update_monitor_config_in_catraca(self, instance):
        """
        Atualiza configurações de monitor NA CATRACA
        
        Envia via set_configuration.fcgi o bloco 'monitor' com:
        - request_timeout: tempo de timeout das requisições HTTP
        - hostname: servidor que vai receber as notificações
        - port: porta do servidor
        - path: endpoint/path onde enviar
        """
        try:
            # Monta o payload com os campos do monitor
            monitor_data = {}
            
            if hasattr(instance, 'request_timeout') and instance.request_timeout is not None:
                monitor_data['request_timeout'] = str(instance.request_timeout)
            
            # Removemos a verificação "and instance.hostname" para permitir enviar string vazia (limpar config)
            if hasattr(instance, 'hostname'):
                monitor_data['hostname'] = str(instance.hostname or "")
            
            if hasattr(instance, 'port'):
                monitor_data['port'] = str(instance.port or "")
            
            if hasattr(instance, 'path'):
                monitor_data['path'] = str(instance.path or "")
            
            # Campos extras que podem existir em algumas catracas
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
        """
        Sincroniza configurações de monitor DA CATRACA para o sistema
        
        Busca via get_configuration.fcgi o bloco 'monitor' que contém
        as configurações atuais do sistema de push de logs.
        
        Formato correto do payload:
        {
            "monitor": ["path", "hostname", "port", "request_timeout"]
        }
        """
        try:
            # Payload correto: lista de campos a buscar
            payload = {
                "monitor": [
                    "path",
                    "hostname", 
                    "port",
                    "request_timeout",
                    "alive_interval",
                    "inform_access_event_id"
                ]
            }
            
            response = self._make_request("get_configuration.fcgi", json_data=payload)
            
            if response.status_code != 200:
                return Response({
                    "success": False,
                    "error": f"Erro ao buscar configurações: HTTP {response.status_code}",
                    "details": response.text
                }, status=response.status_code)
            
            data = response.json() or {}
            monitor_data = data.get("monitor", {})
            
            # Verifica se retornou dados do monitor
            if isinstance(monitor_data, dict) and monitor_data:
                # Sucesso - retorna os dados
                return Response({
                    "success": True,
                    "monitor": monitor_data,
                    "message": "Configurações de monitor obtidas com sucesso"
                }, status=status.HTTP_200_OK)
            
            # Monitor não configurado (campos vazios ou inexistentes)
            # Isso é NORMAL - monitor é OPCIONAL
            return Response({
                "success": False,
                "error": "Dispositivo não tem monitor configurado",
                "hint": "Monitor é opcional. Use POST /monitor-configs/ para configurar.",
                "is_configuration_missing": True  # Flag para indicar que não é erro crítico
            }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Erro ao sincronizar configurações: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def sync_monitor_into_model(self):
        """
        Sincroniza da catraca e persiste no model MonitorConfig
        
        Busca as configurações da catraca e atualiza/cria o MonitorConfig local
        """
        try:
            from ..models import MonitorConfig
            
            # Busca da catraca
            response = self.sync_monitor_config_from_catraca()
            
            if response.status_code != 200:
                return response
            
            monitor_data = response.data.get('monitor', {})
            
            if not monitor_data:
                return Response({
                    "success": False,
                    "error": "Nenhum dado de monitor retornado"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Atualiza ou cria o MonitorConfig
            config, created = MonitorConfig.objects.update_or_create(
                device=self.device,
                defaults={
                    'request_timeout': int(monitor_data.get('request_timeout', 1000)),
                    'hostname': monitor_data.get('hostname', ''),
                    'port': monitor_data.get('port', ''),
                    'path': monitor_data.get('path', 'api/notifications'),
                }
            )
            
            action = "criada" if created else "atualizada"
            
            return Response({
                "success": True,
                "message": f"Configuração de monitor {action} com sucesso",
                "config_id": config.id,
                "is_configured": config.is_configured,
                "full_url": config.full_url,
                "monitor_data": monitor_data
            }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Erro ao persistir configuração: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
