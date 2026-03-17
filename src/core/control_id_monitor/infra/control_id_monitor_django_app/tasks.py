from datetime import timedelta
import logging

from celery import shared_task
from django.utils import timezone

from .models import MonitorConfig
from .monitoring import mark_monitor_config_offline

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def check_monitor_heartbeats(self):
    now = timezone.now()
    checked = 0
    offline_marked = 0

    queryset = (
        MonitorConfig.objects.select_related("device")
        .filter(device__is_active=True)
        .exclude(hostname="")
    )

    for config in queryset:
        if (
            config.offline_detection_paused_until
            and config.offline_detection_paused_until > now
        ):
            continue

        checked += 1
        reference_time = config.last_seen_at or config.updated_at
        timeout_seconds = max(int(config.heartbeat_timeout_seconds or 300), 30)

        if now - reference_time > timedelta(seconds=timeout_seconds):
            if mark_monitor_config_offline(config, detected_at=now):
                offline_marked += 1
                logger.warning(
                    "[MONITOR_HEARTBEAT] Catraca %s marcada offline",
                    config.device.name,
                )

    return {
        "checked": checked,
        "offline_marked": offline_marked,
        "timestamp": now.isoformat(),
    }
