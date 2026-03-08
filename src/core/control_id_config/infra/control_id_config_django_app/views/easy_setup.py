"""
Easy Setup — Views para reset e reconfiguração de catracas.

GET  /api/config/easy-setup/         → Lista devices disponíveis
POST /api/config/easy-setup/         → Dispara setup assíncrono (Celery)
GET  /api/config/easy-setup/status/  → Consulta andamento
GET  /api/config/easy-setup/history/ → Histórico de execuções
"""

import uuid as _uuid

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.core.control_Id.infra.control_id_django_app.models import Device
from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import (
    MonitorConfig,
)
from src.core.user.infra.user_django_app.models import User

# Re-export para manter compatibilidade com imports existentes
from .easy_setup_engine import _EasySetupEngine  # noqa: F401


# ═══════════════════════════════════════════════════════════════════════════════
#  Views
# ═══════════════════════════════════════════════════════════════════════════════


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def easy_setup(request):
    """
    GET  → Lista devices disponíveis para setup.
    POST → Executa reset + reconfiguração nos devices selecionados.
           Body: {"device_ids": [1, 2, 3]}  (todos se omitido)
    """
    if request.method == "GET":
        return _list_devices(request)
    return _execute_setup(request)


def _list_devices(request):
    """Retorna devices ativos com informações úteis para o frontend."""
    devices = Device.objects.filter(is_active=True).order_by("name")
    device_list = []
    global_user_count = User.objects.exclude(is_staff=True, is_superuser=True).count()
    reference_monitor = (
        MonitorConfig.objects.filter(device__is_default=True)
        .exclude(hostname="")
        .first()
        or MonitorConfig.objects.exclude(hostname="").first()
    )

    for d in devices:
        monitor = MonitorConfig.objects.filter(device=d).first()
        effective_monitor = (
            monitor if monitor and monitor.is_configured else reference_monitor
        )

        device_list.append(
            {
                "id": d.id,
                "name": d.name,
                "ip": d.ip,
                "is_default": d.is_default,
                "user_count": global_user_count,
                "monitor_configured": (
                    effective_monitor.is_configured if effective_monitor else False
                ),
                "monitor_url": (
                    effective_monitor.full_url
                    if effective_monitor and effective_monitor.is_configured
                    else None
                ),
                "selected": True,  # Por padrão todas marcadas
            }
        )

    return Response(
        {
            "devices": device_list,
            "total": len(device_list),
            "hint": 'POST com {"device_ids": [1,2]} para executar o setup. '
            "Omita device_ids para executar em todos.",
        }
    )


def _execute_setup(request):
    """Dispara o Easy Setup como Celery task assíncrona."""
    from ..models import EasySetupLog
    from ..tasks import run_easy_setup_task

    device_ids = request.data.get("device_ids")

    if device_ids is not None and not isinstance(device_ids, list):
        return Response(
            {"error": "device_ids deve ser uma lista de IDs ou omitido"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if device_ids == []:
        return Response(
            {"error": "Selecione ao menos um device para executar o setup"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if device_ids is not None:
        devices = Device.objects.filter(id__in=device_ids, is_active=True)
        missing = set(device_ids) - set(devices.values_list("id", flat=True))
        if missing:
            return Response(
                {
                    "error": f"Devices não encontrados ou inativos: {list(missing)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        devices = Device.objects.filter(is_active=True)

    if not devices.exists():
        return Response(
            {"error": "Nenhuma catraca ativa encontrada"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Gerar task_id único para agrupar logs desta execução
    task_id = str(_uuid.uuid4())
    resolved_ids = list(devices.values_list("id", flat=True))

    # Criar logs PENDING para cada device (frontend já pode ver)
    for device in devices:
        EasySetupLog.objects.create(
            task_id=task_id,
            device=device,
            status=EasySetupLog.Status.PENDING,
        )

    # Disparar task assíncrona
    run_easy_setup_task.delay(resolved_ids, task_id)

    return Response(
        {
            "task_id": task_id,
            "message": f"Easy Setup iniciado para {len(resolved_ids)} device(s)",
            "device_ids": resolved_ids,
            "status_url": f"easy-setup/status/{task_id}/",
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def easy_setup_status(request, task_id):
    """
    Consulta o andamento/resultado de uma execução do Easy Setup.
    Retorna status individual de cada device + resumo geral.
    """
    from ..models import EasySetupLog

    logs = EasySetupLog.objects.filter(task_id=task_id).select_related("device")
    if not logs.exists():
        return Response(
            {"error": "Task não encontrada"},
            status=status.HTTP_404_NOT_FOUND,
        )

    devices_data = []
    for log in logs:
        entry = {
            "device_id": log.device_id,
            "device_name": log.device.name,
            "status": log.status,
            "started_at": log.started_at,
            "finished_at": log.finished_at,
        }
        # Só inclui report completo se já finalizou
        if log.status not in (
            EasySetupLog.Status.PENDING,
            EasySetupLog.Status.RUNNING,
        ):
            entry["report"] = log.report
        devices_data.append(entry)

    # Status geral
    statuses = [l.status for l in logs]
    if all(s == EasySetupLog.Status.PENDING for s in statuses):
        overall = "pending"
    elif any(s == EasySetupLog.Status.RUNNING for s in statuses):
        overall = "running"
    elif any(s == EasySetupLog.Status.PENDING for s in statuses):
        overall = "running"  # Ainda tem devices na fila
    elif all(s == EasySetupLog.Status.SUCCESS for s in statuses):
        overall = "success"
    elif all(s == EasySetupLog.Status.FAILED for s in statuses):
        overall = "failed"
    else:
        overall = "partial"

    return Response(
        {
            "task_id": task_id,
            "overall_status": overall,
            "devices": devices_data,
            "total": len(devices_data),
            "completed": sum(
                1
                for s in statuses
                if s not in (EasySetupLog.Status.PENDING, EasySetupLog.Status.RUNNING)
            ),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def easy_setup_history(request):
    """
    Lista execuções recentes do Easy Setup (agrupadas por task_id).
    Query params: ?limit=10
    """
    from ..models import EasySetupLog

    limit = int(request.query_params.get("limit", 10))

    # Buscar task_ids distintos mais recentes
    task_ids = (
        EasySetupLog.objects.order_by("-started_at")
        .values_list("task_id", flat=True)
        .distinct()[:limit]
    )

    executions = []
    for tid in task_ids:
        logs = EasySetupLog.objects.filter(task_id=tid).select_related("device")
        statuses = [l.status for l in logs]

        if all(s == EasySetupLog.Status.SUCCESS for s in statuses):
            overall = "success"
        elif all(s == EasySetupLog.Status.FAILED for s in statuses):
            overall = "failed"
        elif any(
            s in (EasySetupLog.Status.PENDING, EasySetupLog.Status.RUNNING)
            for s in statuses
        ):
            overall = "running"
        else:
            overall = "partial"

        executions.append(
            {
                "task_id": tid,
                "overall_status": overall,
                "devices": [
                    {
                        "device_name": l.device.name,
                        "status": l.status,
                        "elapsed_s": l.report.get("elapsed_s") if l.report else None,
                    }
                    for l in logs
                ],
                "started_at": min(l.started_at for l in logs),
                "total_devices": len(logs),
            }
        )

    return Response({"executions": executions})
