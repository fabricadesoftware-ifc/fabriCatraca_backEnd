from django.db import transaction
from django.utils import timezone
from django.utils.timezone import localtime

from src.core.control_Id.infra.control_id_django_app.models import Device

from .models import MonitorAlert, MonitorConfig


def resolve_monitor_device(device_identifier):
    device = None
    if device_identifier not in (None, ""):
        try:
            device = Device.objects.filter(id=int(device_identifier)).first()
        except (TypeError, ValueError):
            device = None

    if device:
        return device

    monitor_cfg = (
        MonitorConfig.objects.select_related("device")
        .filter(device__is_active=True)
        .exclude(hostname="")
        .first()
    )
    if monitor_cfg:
        return monitor_cfg.device

    return Device.objects.filter(is_default=True).first() or Device.objects.filter(is_active=True).first()


@transaction.atomic
def touch_device_heartbeat(device_identifier, source="monitor"):
    device = resolve_monitor_device(device_identifier)
    if not device:
        return None

    now = timezone.now()
    config, _ = MonitorConfig.objects.select_for_update().get_or_create(device=device)
    was_offline = config.is_offline
    config.last_seen_at = now
    config.last_payload_at = now
    config.last_signal_source = source
    config.is_offline = False
    config.offline_since = None
    config.save(
        update_fields=[
            "last_seen_at",
            "last_payload_at",
            "last_signal_source",
            "is_offline",
            "offline_since",
            "updated_at",
        ]
    )

    if was_offline:
        MonitorAlert.objects.filter(
            device=device,
            type=MonitorAlert.AlertType.DEVICE_OFFLINE,
            is_active=True,
        ).update(is_active=False, resolved_at=now)

    return config


@transaction.atomic
def mark_monitor_config_offline(config, detected_at=None):
    detected_at = detected_at or timezone.now()
    config = MonitorConfig.objects.select_for_update().select_related("device").get(pk=config.pk)

    if config.is_offline:
        return None

    config.is_offline = True
    config.offline_since = detected_at
    config.save(update_fields=["is_offline", "offline_since", "updated_at"])

    existing = MonitorAlert.objects.filter(
        device=config.device,
        type=MonitorAlert.AlertType.DEVICE_OFFLINE,
        is_active=True,
    ).first()
    if existing:
        return existing

    formatted_time = localtime(detected_at).strftime("%d/%m/%Y %H:%M")
    return MonitorAlert.objects.create(
        type=MonitorAlert.AlertType.DEVICE_OFFLINE,
        severity=MonitorAlert.Severity.ERROR,
        title=f"Catraca {config.device.name} ficou offline",
        message=f"A catraca {config.device.name} ficou offline as {formatted_time} e ainda nao voltou.",
        device=config.device,
        dedupe_key=f"device-offline:{config.device_id}",
        metadata={
            "device_id": config.device_id,
            "device_name": config.device.name,
            "offline_since": detected_at.isoformat(),
        },
        started_at=detected_at,
        is_active=True,
    )
