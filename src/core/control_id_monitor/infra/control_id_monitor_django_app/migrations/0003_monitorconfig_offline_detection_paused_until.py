from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_monitor_django_app", "0002_monitor_alerts_and_heartbeat"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitorconfig",
            name="offline_detection_paused_until",
            field=models.DateTimeField(
                blank=True,
                help_text="Pausa temporaria da deteccao de offline durante manutencao/easy setup",
                null=True,
            ),
        ),
    ]
