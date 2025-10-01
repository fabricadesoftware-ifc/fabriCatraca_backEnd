from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from celery.result import AsyncResult

from .device_config_view import DeviceConfigView
from ..tasks import run_config_sync


@extend_schema(tags=["Config Sync"])
@api_view(['GET'])
def sync_all_configs(request):
    """Dispara sincronização de configurações de forma assíncrona via Celery"""
    task = run_config_sync.delay()
    return Response({
        "task_id": task.id,
        "status": "queued",
        "message": "Sincronização de configurações iniciada"
    }, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Config Sync"])
@api_view(['GET'])
def sync_config_status(request):
    """Verifica status de uma task de sincronização de configurações"""
    task_id = request.query_params.get('task_id')
    if not task_id:
        return Response(
            {"error": "task_id é obrigatório"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = AsyncResult(task_id)
    payload = {
        "task_id": task_id,
        "state": result.state,
    }
    
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
    
    return Response(payload)


@extend_schema(tags=["Config Sync"])
@api_view(['GET', 'POST'])
def sync_device_config(request, device_id: int):
    """
    GET: retorna configs atuais do device
    POST: sincroniza com a catraca e retorna configs atualizadas
    """
    try:
        from src.core.control_Id.infra.control_id_django_app.models import Device
        from ..models import SystemConfig, HardwareConfig, SecurityConfig, UIConfig
        from ..serializers import (
            SystemConfigSerializer, HardwareConfigSerializer, 
            SecurityConfigSerializer, UIConfigSerializer, MonitorConfigSerializer
        )
        from ..mixins import UnifiedConfigSyncMixin
        
        device = Device.objects.get(id=device_id)

        if request.method == 'GET':
            # Retorna configurações atuais
            sys_cfg = SystemConfig.objects.filter(device=device).first()
            hw_cfg = HardwareConfig.objects.filter(device=device).first()
            sec_cfg = SecurityConfig.objects.filter(device=device).first()
            ui_cfg = UIConfig.objects.filter(device=device).first()

            return Response({
                'device_id': device.id,
                'device_name': device.name,
                'system': SystemConfigSerializer(sys_cfg).data if sys_cfg else None,
                'hardware': HardwareConfigSerializer(hw_cfg).data if hw_cfg else None,
                'security': SecurityConfigSerializer(sec_cfg).data if sec_cfg else None,
                'ui': UIConfigSerializer(ui_cfg).data if ui_cfg else None,
            })

        elif request.method == 'POST':
            # Sincroniza com a catraca
            sync = UnifiedConfigSyncMixin()
            sync.set_device(device)
            
            sys_res = sync.sync_system_config_from_catraca()
            hw_res = sync.sync_hardware_config_from_catraca()
            sec_res = sync.sync_security_config_from_catraca()
            ui_res = sync.sync_ui_config_from_catraca()
            mon_res = sync.sync_monitor_config_from_catraca()

            return Response({
                'message': 'Sincronização de configurações concluída',
                'results': {
                    'system': getattr(sys_res, 'data', sys_res),
                    'hardware': getattr(hw_res, 'data', hw_res),
                    'security': getattr(sec_res, 'data', sec_res),
                    'ui': getattr(ui_res, 'data', ui_res),
                    'monitor': getattr(mon_res, 'data', mon_res),
                }
            })

    except Device.DoesNotExist:
        return Response(
            {"error": "Dispositivo não encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
