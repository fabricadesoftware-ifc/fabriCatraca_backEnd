from django.conf import settings
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


@transaction.atomic
def create_temporary_release_delay_alert(release, consumed_log, consumed_at=None):
    consumed_at = consumed_at or getattr(consumed_log, "time", None)
    activated_at = getattr(release, "activated_at", None) or getattr(release, "valid_from", None)
    if not consumed_at or not activated_at:
        return None

    delay_seconds = int((consumed_at - activated_at).total_seconds())
    threshold_seconds = int(
        getattr(settings, "TEMPORARY_RELEASE_DELAY_ALERT_SECONDS", 300) or 300
    )
    if delay_seconds <= threshold_seconds:
        return None

    dedupe_key = f"temporary-release-delay:{release.id}"
    existing = MonitorAlert.objects.filter(dedupe_key=dedupe_key).first()
    if existing:
        return existing

    delay_minutes = round(delay_seconds / 60, 1)
    started_label = localtime(activated_at).strftime("%d/%m/%Y %H:%M")
    consumed_label = localtime(consumed_at).strftime("%d/%m/%Y %H:%M")
    portal_name = getattr(getattr(consumed_log, "portal", None), "name", None)
    device = getattr(consumed_log, "device", None)
    device_name = getattr(device, "name", "") if device else ""
    user_name = getattr(getattr(release, "user", None), "name", "Usuário")

    message = (
        f"{user_name} foi liberado às {started_label} e só passou às {consumed_label} "
        f"({delay_minutes} min depois)."
    )
    if portal_name:
        message += f" Portal: {portal_name}."
    if device_name:
        message += f" Catraca: {device_name}."

    return MonitorAlert.objects.create(
        type=MonitorAlert.AlertType.AUTHORIZED_EXIT_DELAY,
        severity=MonitorAlert.Severity.WARNING,
        title=f"{user_name} passou bem depois da liberação",
        message=message,
        device=device,
        user=getattr(release, "user", None),
        dedupe_key=dedupe_key,
        metadata={
            "temporary_release_id": release.id,
            "delay_seconds": delay_seconds,
            "delay_minutes": delay_minutes,
            "consumed_at": consumed_at.isoformat(),
            "activated_at": activated_at.isoformat(),
            "portal_name": portal_name,
            "device_name": device_name,
        },
        started_at=consumed_at,
        is_active=True,
    )
