import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)


class TemporaryUserReleaseNotificationService:
    @staticmethod
    def _format_datetime(value):
        localized_value = timezone.localtime(value)
        return localized_value.strftime("%d/%m/%Y"), localized_value.strftime("%H:%M")

    @staticmethod
    def _target_label(user):
        role = getattr(user, "effective_app_role", None) or getattr(user, "app_role", "")
        if role == User.AppRole.ALUNO:
            return "aluno"
        if role == User.AppRole.SERVIDOR:
            return "servidor"
        return "usuario"

    @classmethod
    def build_subject(cls, release):
        return f"Liberacao temporaria registrada para {release.user.name}"

    @classmethod
    def _build_fallback_message(cls, release):
        release_date, release_time = cls._format_datetime(release.valid_from)
        valid_until_date, valid_until_time = cls._format_datetime(release.valid_until)
        target_label = cls._target_label(release.user)
        requester_name = release.requested_by.name or "Sistema"
        notes = (release.notes or "Nao informado").strip() or "Nao informado"

        return (
            "Caro(a) professor(a),\n\n"
            f"O {target_label} {release.user.name} foi liberado no dia {release_date} "
            f"as {release_time} pelo motivo de {notes}.\n\n"
            f"A liberacao permanece valida ate {valid_until_date} as {valid_until_time}.\n"
            f"Solicitado por: {requester_name}.\n"
        )

    @classmethod
    def build_message(cls, release):
        message = (getattr(release, "notification_message", "") or "").strip()
        if message:
            return message
        return cls._build_fallback_message(release)

    @classmethod
    def notify_release_created(cls, release):
        notified_server = release.notified_server
        if not notified_server or not notified_server.email:
            return

        send_mail(
            subject=cls.build_subject(release),
            message=cls.build_message(release),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[notified_server.email],
            fail_silently=False,
        )

        logger.info(
            "Temporary release notification sent to %s for release %s",
            notified_server.email,
            release.id,
        )
