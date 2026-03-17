from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("control_id_monitor_django_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitorconfig",
            name="heartbeat_timeout_seconds",
            field=models.PositiveIntegerField(default=300, help_text="Segundos sem sinais antes de considerar a catraca offline"),
        ),
        migrations.AddField(
            model_name="monitorconfig",
            name="is_offline",
            field=models.BooleanField(default=False, help_text="Indica se a catraca esta atualmente sem sinais dentro do timeout"),
        ),
        migrations.AddField(
            model_name="monitorconfig",
            name="last_payload_at",
            field=models.DateTimeField(blank=True, help_text="Ultimo payload recebido do monitor da catraca", null=True),
        ),
        migrations.AddField(
            model_name="monitorconfig",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, help_text="Ultimo instante em que o backend recebeu sinal da catraca", null=True),
        ),
        migrations.AddField(
            model_name="monitorconfig",
            name="last_signal_source",
            field=models.CharField(blank=True, default="", help_text="Origem do ultimo sinal recebido (alive, dao, catra_event)", max_length=64),
        ),
        migrations.AddField(
            model_name="monitorconfig",
            name="offline_since",
            field=models.DateTimeField(blank=True, help_text="Instante em que a catraca foi considerada offline", null=True),
        ),
        migrations.CreateModel(
            name="MonitorAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(choices=[("device_offline", "Catraca Offline"), ("authorized_exit_delay", "Saida com atraso"), ("generic", "Generico")], default="generic", max_length=64)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error")], default="warning", max_length=16)),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("dedupe_key", models.CharField(blank=True, db_index=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("resolved_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("device", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitor_alerts", to="control_id_django_app.device")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitor_alerts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Alerta de Monitor",
                "verbose_name_plural": "Alertas de Monitor",
                "ordering": ("-is_active", "-started_at", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="MonitorAlertRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("read_at", models.DateTimeField(auto_now_add=True)),
                ("alert", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reads", to="control_id_monitor_django_app.monitoralert")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monitor_alert_reads", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Leitura de Alerta",
                "verbose_name_plural": "Leituras de Alertas",
            },
        ),
        migrations.AddConstraint(
            model_name="monitoralertread",
            constraint=models.UniqueConstraint(fields=("alert", "user"), name="unique_monitor_alert_read"),
        ),
    ]
