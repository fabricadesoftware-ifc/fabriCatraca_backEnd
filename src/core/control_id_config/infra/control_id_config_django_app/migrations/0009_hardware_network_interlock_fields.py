from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_config_django_app", "0008_fix_existing_config_field_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="hardwareconfig",
            name="network_interlock_api_bypass_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Ignorar intertravamento via rede ao abrir pela API",
            ),
        ),
        migrations.AddField(
            model_name="hardwareconfig",
            name="network_interlock_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Habilitar intertravamento via rede",
            ),
        ),
        migrations.AddField(
            model_name="hardwareconfig",
            name="network_interlock_rex_bypass_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Ignorar intertravamento via rede ao abrir via botoeira",
            ),
        ),
    ]
