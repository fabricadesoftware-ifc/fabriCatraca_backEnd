from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from src.core.control_id.infra.control_id_django_app.models import (
    AccessRule,
    CustomGroup,
    TemporaryGroupRelease,
    TemporaryUserRelease,
)
from src.core.control_id.infra.control_id_django_app.tasks import (
    send_temporary_group_release_notification,
    send_temporary_user_release_notification,
)
from src.core.user.infra.user_django_app.models import User


class TemporaryReleaseNotificationTests(APITestCase):
    def setUp(self):
        self.operator = User.objects.create_user(
            email="operador@example.com",
            name="Operador",
            password="123456",
            app_role=User.AppRole.ADMIN,
        )
        self.target_user = User.objects.create_user(
            email="alvo@example.com",
            name="Usuario Alvo",
            password="123456",
        )
        self.group = CustomGroup.objects.create(name="1INFO1")
        self.access_rule = AccessRule.objects.create(
            name="Regra Temporaria Global",
            type=1,
            priority=99,
        )
        self.client.force_authenticate(user=self.operator)

    def test_user_release_accepts_multiple_notification_emails(self):
        with (
            self.settings(TEMPORARY_RELEASE_ACCESS_RULE_ID=self.access_rule.id),
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "send_temporary_user_release_notification.delay"
            ) as mock_email_delay,
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "activate_user_release.apply_async"
            ),
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "expire_user_release.apply_async"
            ),
        ):
            response = self.client.post(
                reverse("temporaryuserrelease-list"),
                {
                    "user_id": self.target_user.id,
                    "duration_minutes": 10,
                    "notes": "Liberacao para entrada",
                    "notification_email": (
                        "Professor@Example.com, coordenacao@example.com; professor@example.com"
                    ),
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        release = TemporaryUserRelease.objects.get(id=response.data["id"])
        self.assertEqual(
            release.notification_email,
            "professor@example.com, coordenacao@example.com",
        )
        self.assertEqual(response.data["notification_status"], "queued")
        mock_email_delay.assert_called_once_with(release.id)

    def test_group_release_accepts_multiple_notification_emails(self):
        with (
            self.settings(TEMPORARY_RELEASE_ACCESS_RULE_ID=self.access_rule.id),
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "send_temporary_group_release_notification.delay"
            ) as mock_email_delay,
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "activate_group_release.apply_async"
            ),
            patch(
                "src.core.control_id.infra.control_id_django_app.tasks."
                "expire_group_release.apply_async"
            ),
        ):
            response = self.client.post(
                reverse("temporarygrouprelease-list"),
                {
                    "group_id": self.group.id,
                    "duration_minutes": 10,
                    "notes": "Aula externa",
                    "notification_email": (
                        "professor@example.com\ncoordenacao@example.com"
                    ),
                    "notification_message": "Turma liberada para aula externa.",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        release = TemporaryGroupRelease.objects.get(id=response.data["id"])
        self.assertEqual(
            release.notification_email,
            "professor@example.com, coordenacao@example.com",
        )
        self.assertEqual(
            release.notification_message,
            "Turma liberada para aula externa.",
        )
        self.assertEqual(response.data["notification_status"], "queued")
        mock_email_delay.assert_called_once_with(release.id)

    def test_user_notification_task_sends_to_multiple_recipients(self):
        release = TemporaryUserRelease.objects.create(
            user=self.target_user,
            requested_by=self.operator,
            access_rule=self.access_rule,
            status=TemporaryUserRelease.Status.PENDING,
            notes="Liberacao para entrada",
            notification_email="professor@example.com, coordenacao@example.com",
            notification_message="Usuario liberado.",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(minutes=10),
        )

        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="nao-responda@example.com",
        ):
            result = send_temporary_user_release_notification.run(release.id)

        self.assertTrue(result["success"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["professor@example.com", "coordenacao@example.com"],
        )
        self.assertEqual(mail.outbox[0].body, "Usuario liberado.")

    def test_group_notification_task_sends_to_multiple_recipients(self):
        release = TemporaryGroupRelease.objects.create(
            group=self.group,
            requested_by=self.operator,
            access_rule=self.access_rule,
            status=TemporaryGroupRelease.Status.PENDING,
            notes="Aula externa",
            notification_email="professor@example.com, coordenacao@example.com",
            notification_message="Turma liberada.",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(minutes=10),
        )

        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="nao-responda@example.com",
        ):
            result = send_temporary_group_release_notification.run(release.id)

        self.assertTrue(result["success"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["professor@example.com", "coordenacao@example.com"],
        )
        self.assertIn(self.group.name, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].body, "Turma liberada.")
