from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_monitor_django_app", "0003_monitorconfig_offline_detection_paused_until"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitorconfig",
            name="auto_disabled_due_to_offline",
            field=models.BooleanField(
                default=False,
                help_text="Indica se a catraca foi desativada automaticamente por ter ficado offline",
            ),
        ),
    ]
