from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from src.core.control_Id.infra.control_id_django_app.models import (
    AccessLogs,
    AccessRule,
    Device,
    TemporaryUserRelease,
    UserAccessRule,
)
from src.core.control_Id.infra.control_id_django_app.tasks import (
    process_temporary_user_releases,
)
from src.core.user.infra.user_django_app.models import User


class TemporaryUserReleaseTests(APITestCase):
    def setUp(self):
        self.operator = User.objects.create_user(
            email="operador@example.com",
            name="Operador",
            password="123456",
        )
        self.target_user = User.objects.create_user(
            email="alvo@example.com",
            name="Usuario Alvo",
            password="123456",
        )
        self.access_rule = AccessRule.objects.create(
            name="Regra Temporaria Global",
            type=1,
            priority=99,
        )
        self.device = Device.objects.create(
            name="Catraca 1",
            ip="127.0.0.1",
            username="admin",
            password="admin",
            is_active=True,
            is_default=True,
        )
        self.client.force_authenticate(user=self.operator)

    def _create_active_release(self, valid_until=None):
        user_access_rule = UserAccessRule.objects.create(
            user=self.target_user,
            access_rule=self.access_rule,
        )
        return TemporaryUserRelease.objects.create(
            user=self.target_user,
            requested_by=self.operator,
            access_rule=self.access_rule,
            user_access_rule=user_access_rule,
            status=TemporaryUserRelease.Status.ACTIVE,
            valid_from=timezone.now() - timedelta(minutes=5),
            valid_until=valid_until or (timezone.now() + timedelta(minutes=5)),
            activated_at=timezone.now() - timedelta(minutes=4),
        )

    def test_create_temporary_release_persists_requested_by(self):
        with self.settings(TEMPORARY_RELEASE_ACCESS_RULE_ID=self.access_rule.id):
            response = self.client.post(
                reverse("temporaryuserrelease-list"),
                {
                    "user_id": self.target_user.id,
                    "duration_minutes": 10,
                    "notes": "Liberacao para entrada",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        release = TemporaryUserRelease.objects.get(id=response.data["id"])
        self.assertEqual(release.requested_by, self.operator)
        self.assertEqual(release.user, self.target_user)
        self.assertEqual(release.access_rule, self.access_rule)

    def test_task_activates_pending_release(self):
        release = TemporaryUserRelease.objects.create(
            user=self.target_user,
            requested_by=self.operator,
            access_rule=self.access_rule,
            status=TemporaryUserRelease.Status.PENDING,
            valid_from=timezone.now() - timedelta(minutes=1),
            valid_until=timezone.now() + timedelta(minutes=5),
        )

        with patch(
            "src.core.control_Id.infra.control_id_django_app.temporary_release_service."
            "TemporaryUserReleaseService.create_in_catraca",
            return_value=Response({"success": True}, status=status.HTTP_201_CREATED),
        ):
            result = process_temporary_user_releases.run()

        release.refresh_from_db()
        self.assertTrue(result["success"])
        self.assertEqual(release.status, TemporaryUserRelease.Status.ACTIVE)
        self.assertIsNotNone(release.user_access_rule)
        self.assertEqual(UserAccessRule.objects.count(), 1)

    def test_task_consumes_release_when_access_log_is_found(self):
        release = self._create_active_release()

        access_log = AccessLogs.objects.create(
            time=timezone.now(),
            event_type=7,
            device=self.device,
            identifier_id="123",
            user=self.target_user,
            portal=None,
            access_rule=self.access_rule,
            qr_code="",
            uhf_value="",
            pin_value="",
            card_value="",
            confidence=0,
            mask="",
        )

        with patch(
            "src.core.control_Id.infra.control_id_django_app.temporary_release_service."
            "TemporaryUserReleaseService.delete_in_catraca",
            return_value=Response({"success": True}, status=status.HTTP_204_NO_CONTENT),
        ):
            process_temporary_user_releases.run()

        release.refresh_from_db()
        self.assertEqual(release.status, TemporaryUserRelease.Status.CONSUMED)
        self.assertEqual(release.consumed_log, access_log)
        self.assertFalse(UserAccessRule.objects.filter(id=release.user_access_rule_id).exists())

    def test_task_expires_release_without_usage(self):
        release = self._create_active_release(
            valid_until=timezone.now() - timedelta(minutes=1)
        )

        with patch(
            "src.core.control_Id.infra.control_id_django_app.temporary_release_service."
            "TemporaryUserReleaseService.delete_in_catraca",
            return_value=Response({"success": True}, status=status.HTTP_204_NO_CONTENT),
        ):
            process_temporary_user_releases.run()

        release.refresh_from_db()
        self.assertEqual(release.status, TemporaryUserRelease.Status.EXPIRED)
        self.assertIn("não utilizou", release.result_message.lower())
        self.assertEqual(UserAccessRule.objects.count(), 0)
