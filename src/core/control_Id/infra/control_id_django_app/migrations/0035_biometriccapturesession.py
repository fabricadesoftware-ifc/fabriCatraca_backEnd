import uuid

from django.conf import settings
from django.db import migrations, models
import src.core.control_id.infra.control_id_django_app.models.biometric_capture_session


class Migration(migrations.Migration):
    dependencies = [
        (
            "control_id_django_app",
            "0034_alter_accessrule_options_alter_portal_options_and_more",
        ),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BiometricCaptureSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("deleted", models.DateTimeField(editable=False, null=True)),
                (
                    "deleted_by_cascade",
                    models.BooleanField(default=False, editable=False),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sensor_identifier",
                    models.CharField(default="local-default", max_length=100),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("processing", "Processando"),
                            ("completed", "Concluida"),
                            ("failed", "Falhou"),
                            ("expired", "Expirada"),
                            ("cancelled", "Cancelada"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "token",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("attempts", models.JSONField(blank=True, default=list)),
                ("selected_quality", models.IntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "expires_at",
                    models.DateTimeField(
                        default=src.core.control_id.infra.control_id_django_app.models.biometric_capture_session.default_capture_session_expiration
                    ),
                ),
                (
                    "extractor_device",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="biometric_capture_sessions",
                        to="control_id_django_app.device",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="requested_biometric_capture_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="capture_sessions",
                        to="control_id_django_app.template",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="biometric_capture_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sessao de Captura Biometrica",
                "verbose_name_plural": "Sessoes de Captura Biometrica",
                "db_table": "biometric_capture_sessions",
                "ordering": ["-created_at"],
            },
        ),
    ]
