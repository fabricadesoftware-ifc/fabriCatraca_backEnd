"""
Handlers para processar notificações recebidas do Monitor da Catraca

O Monitor é um sistema PUSH onde a catraca envia automaticamente:
- Logs de acesso (access_logs)
- Templates (biometria)
- Cartões (cards)
- Alarmes (alarm_logs)

Quando há inserção, alteração ou deleção dessas entidades.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.db import transaction
import logging

from .access_verification import access_verifier

logger = logging.getLogger(__name__)


class MonitorNotificationHandler:
    """
    Processa notificações enviadas pela catraca via Monitor
    
    Formato esperado:
    {
        "object_changes": [
            {
                "object": "access_logs",
                "type": "inserted",
                "values": {
                    "id": "519",
                    "time": "1532977090",
                    "event": "12",
                    "device_id": "478435",
                    ...
                }
            }
        ],
        "device_id": 478435
    }
    """
    
    def __init__(self):
        self.handlers = {
            'access_logs': self._handle_access_log,
            'templates': self._handle_template,
            'cards': self._handle_card,
            'alarm_logs': self._handle_alarm_log,
        }
    
    def process_notification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma notificação recebida da catraca
        
        Args:
            payload: JSON enviado pela catraca
            
        Returns:
            dict: Resultado do processamento
        """
        try:
            device_id = payload.get('device_id')
            object_changes = payload.get('object_changes', [])
            
            if not device_id:
                logger.error("Notificação sem device_id")
                return {
                    'success': False,
                    'error': 'device_id é obrigatório',
                    'processed': 0
                }
            
            if not object_changes:
                logger.warning(f"Notificação vazia do device {device_id}")
                return {
                    'success': True,
                    'warning': 'Nenhuma mudança recebida',
                    'processed': 0
                }
            
            logger.info(f"📥 [MONITOR] Recebendo {len(object_changes)} mudanças do device {device_id}")
            
            results = []
            processed = 0
            errors = []
            
            with transaction.atomic():
                for change in object_changes:
                    try:
                        result = self._process_single_change(device_id, change)
                        results.append(result)
                        if result.get('success'):
                            processed += 1
                        else:
                            errors.append(result.get('error'))
                    except Exception as e:
                        error_msg = f"Erro processando {change.get('object')}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        errors.append(error_msg)
            
            logger.info(f"✅ [MONITOR] Processados {processed}/{len(object_changes)} do device {device_id}")
            
            return {
                'success': len(errors) == 0,
                'device_id': device_id,
                'total_changes': len(object_changes),
                'processed': processed,
                'errors': errors if errors else None,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ [MONITOR] Erro geral processando notificação: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'processed': 0
            }
    
    def _process_single_change(self, device_id: int, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma única mudança de objeto
        
        Args:
            device_id: ID do dispositivo
            change: Dict com object, type e values
            
        Returns:
            dict: Resultado do processamento
        """
        object_type = change.get('object')
        change_type = change.get('type')  # inserted, updated, deleted
        values = change.get('values', {})
        
        if not object_type:
            return {'success': False, 'error': 'object é obrigatório'}
        
        if not change_type:
            return {'success': False, 'error': 'type é obrigatório'}
        
        handler = self.handlers.get(object_type)
        
        if not handler:
            logger.warning(f"⚠️ [MONITOR] Tipo de objeto não suportado: {object_type}")
            return {
                'success': False,
                'object': object_type,
                'error': f'Tipo de objeto não suportado: {object_type}'
            }
        
        logger.debug(f"🔄 [MONITOR] Processando {object_type} - {change_type}")
        
        return handler(device_id, change_type, values)
    
    def _handle_access_log(self, device_id: int, change_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mudanças em access_logs
        
        Campos principais:
        - id: ID único do log
        - time: Timestamp Unix
        - event: Código do evento (12=acesso liberado, etc)
        - device_id: ID do dispositivo
        - user_id: ID do usuário
        - portal_id: ID do portal (lado da catraca)
        - card_value: Valor do cartão RFID
        """
        from src.core.control_Id.infra.control_id_django_app.models import AccessLogs, Device, Portal
        from src.core.user.infra.user_django_app.models import User
        
        try:
            # Busca o device
            device = Device.objects.filter(id=device_id).first()
            if not device:
                return {
                    'success': False,
                    'object': 'access_logs',
                    'error': f'Device {device_id} não encontrado'
                }
            
            log_id = values.get('id')
            time_unix = values.get('time')
            event = values.get('event')
            
            if change_type == 'inserted':
                # Converte timestamp Unix para datetime
                timestamp = (
                    datetime.fromtimestamp(int(time_unix), tz=dt_timezone.utc)
                    if time_unix
                    else dt_timezone.now()
                )

                # Busca relacionamentos opcionais
                portal = None
                portal_id = values.get('portal_id')
                if portal_id:
                    portal = Portal.objects.filter(id=portal_id).first()
                
                user = None
                user_id = values.get('user_id')
                if user_id and int(user_id) > 0:
                    user = User.objects.filter(id=user_id).first()

                # Cria o log
                log, created = AccessLogs.objects.get_or_create(
                    device=device,
                    identifier_id=str(log_id),
                    time=timestamp,
                    defaults={
                        'id': values.get('id'),
                        'event_type': int(event),
                        'user': user,
                        'portal': portal,
                        'card_value': values.get('card_value', ''),
                        'qr_code': values.get('qr_code', ''),
                        'uhf_value': values.get('uhf_value', ''),
                        'pin_value': values.get('pin_value', ''),
                        'confidence': values.get('confidence', 0),
                        'mask': values.get('mask', ''),
                        'access_rule': values.get('access_rule', None),
                    }
                )
                
                logger.info(f"✅ [ACCESS_LOG] {'Criado' if created else 'Já existia'} log {log_id} do device {device.name}")
                
                # ── Verificação de acesso: loga o MOTIVO no console ──
                if created:
                    try:
                        access_verifier.analyze_access(
                            user_id=values.get('user_id'),
                            portal_id=values.get('portal_id'),
                            event_type=int(event) if event else 0,
                            access_rule_id=values.get('access_rule'),
                            device_name=device.name,
                            access_time=timestamp,
                        )
                    except Exception as verify_err:
                        logger.warning(
                            f"⚠️ [ACCESS_VERIFY] Erro na verificação de acesso: {verify_err}",
                            exc_info=True,
                        )
                
                return {
                    'success': True,
                    'object': 'access_logs',
                    'action': 'created' if created else 'already_exists',
                    'log_id': log_id,
                    'device': device.name
                }
            
            elif change_type == 'updated':
                # Atualiza log existente
                log = AccessLogs.objects.filter(device=device, identifier_id=str(log_id)).first()
                if log:
                    timestamp = datetime.fromtimestamp(int(time_unix), tz=dt_timezone.utc) if time_unix else log.time

                    log.time = timestamp
                    log.event_type = int(event) if event else log.event_type
                    log.card_value = values.get('card_value', log.card_value)
                    log.qr_code = values.get('qr_code', log.qr_code)
                    log.uhf_value = values.get('uhf_value', log.uhf_value)
                    log.pin_value = values.get('pin_value', log.pin_value)
                    log.save()
                    
                    logger.info(f"✅ [ACCESS_LOG] Atualizado log {log_id} do device {device.name}")
                    return {
                        'success': True,
                        'object': 'access_logs',
                        'action': 'updated',
                        'log_id': log_id
                    }
                else:
                    return {
                        'success': False,
                        'object': 'access_logs',
                        'error': f'Log {log_id} não encontrado para atualização'
                    }
            
            elif change_type == 'deleted':
                # Remove log
                deleted_count, _ = AccessLogs.objects.filter(device=device, identifier_id=str(log_id)).delete()
                
                logger.info(f"✅ [ACCESS_LOG] Deletado log {log_id} do device {device.name}")
                return {
                    'success': True,
                    'object': 'access_logs',
                    'action': 'deleted',
                    'deleted_count': deleted_count
                }
            
            else:
                return {
                    'success': False,
                    'object': 'access_logs',
                    'error': f'Tipo de mudança desconhecido: {change_type}'
                }
        
        except Exception as e:
            logger.error(f"❌ [ACCESS_LOG] Erro processando: {e}", exc_info=True)
            return {
                'success': False,
                'object': 'access_logs',
                'error': str(e)
            }
    
    def _handle_template(self, device_id: int, change_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mudanças em templates (biometria)
        
        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(f"📝 [TEMPLATE] {change_type} - Device {device_id} - Template ID {values.get('id')}")
        
        return {
            'success': True,
            'object': 'templates',
            'action': change_type,
            'note': 'Template processado (apenas log por enquanto)'
        }
    
    def _handle_card(self, device_id: int, change_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mudanças em cartões
        
        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(f"💳 [CARD] {change_type} - Device {device_id} - Card ID {values.get('id')}")
        
        return {
            'success': True,
            'object': 'cards',
            'action': change_type,
            'note': 'Cartão processado (apenas log por enquanto)'
        }
    
    def _handle_alarm_log(self, device_id: int, change_type: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mudanças em alarm_logs
        
        Por enquanto apenas loga, mas pode ser expandido
        """
        logger.info(f"🚨 [ALARM] {change_type} - Device {device_id} - Alarm ID {values.get('id')}")
        
        return {
            'success': True,
            'object': 'alarm_logs',
            'action': change_type,
            'note': 'Alarme processado (apenas log por enquanto)'
        }


# Instância global para uso nas views
monitor_handler = MonitorNotificationHandler()
