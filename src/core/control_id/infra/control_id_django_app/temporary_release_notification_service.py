import logging
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.utils import timezone

from src.core.user.infra.user_django_app.models import User

logger = logging.getLogger(__name__)


class TemporaryUserReleaseNotificationService:
    EMAIL_SPLIT_RE = re.compile(r"[;,\n]+")

    @classmethod
    def normalize_email_list(cls, value):
        emails = []
        seen = set()

        for raw_email in cls.EMAIL_SPLIT_RE.split(value or ""):
            email = raw_email.strip().lower()
            if not email:
                continue
            try:
                validate_email(email)
            except ValidationError as exc:
                raise ValueError(f"E-mail invalido: {email}") from exc
            if email in seen:
                continue
            seen.add(email)
            emails.append(email)

        return ", ".join(emails)

    @classmethod
    def get_recipient_list(cls, release):
        recipient_emails = cls.normalize_email_list(
            getattr(release, "notification_email", "") or ""
        )
        if not recipient_emails and getattr(release, "notified_server", None):
            recipient_emails = cls.normalize_email_list(
                release.notified_server.email or ""
            )
        return [email.strip() for email in recipient_emails.split(",") if email.strip()]

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
        if getattr(release, "user_id", None):
            return f"Liberacao temporaria registrada para {release.user.name}"
        return f"Liberacao temporaria registrada para turma {release.group.name}"

    @classmethod
    def _build_fallback_message(cls, release):
        release_date, release_time = cls._format_datetime(release.valid_from)
        valid_until_date, valid_until_time = cls._format_datetime(release.valid_until)
        requester_name = release.requested_by.name or "Sistema"
        notes = (release.notes or "Nao informado").strip() or "Nao informado"

        if getattr(release, "user_id", None):
            target_label = cls._target_label(release.user)
            target_text = f"O {target_label} {release.user.name} foi liberado"
        else:
            target_text = f"A turma {release.group.name} foi liberada"

        return (
            "Caro(a) professor(a),\n\n"
            f"{target_text} no dia {release_date} "
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
        recipient_list = cls.get_recipient_list(release)
        if not recipient_list:
            return

        send_mail(
            subject=cls.build_subject(release),
            message=cls.build_message(release),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=recipient_list,
            fail_silently=False,
        )

        logger.info(
            "Temporary release notification sent to %s for release %s",
            ", ".join(recipient_list),
            release.id,
        )
