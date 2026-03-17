from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_config_django_app", "0007_security_identifier_fields"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="hardwareconfig",
            options={
                "verbose_name": "Configura??o de Hardware",
                "verbose_name_plural": "Configura??es de Hardware",
            },
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="bell_relay",
            field=models.IntegerField(default=2, help_text="Rel? da campainha"),
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="relayN_enabled",
            field=models.BooleanField(default=False, help_text="Habilitar rel? N"),
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="relayN_timeout",
            field=models.IntegerField(default=5, help_text="Timeout do rel? N em segundos"),
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="relayN_auto_close",
            field=models.BooleanField(default=True, help_text="Fechar rel? automaticamente"),
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="doorN_exception_mode",
            field=models.BooleanField(default=False, help_text="Modo de exce??o da porta N"),
        ),
        migrations.AlterField(
            model_name="hardwareconfig",
            name="exception_mode",
            field=models.CharField(
                choices=[("none", "Normal"), ("emergency", "Emerg?ncia"), ("lock_down", "Lockdown")],
                default="none",
                help_text="Modo de exce??o",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="securityconfig",
            name="log_type",
            field=models.BooleanField(
                default=False,
                help_text="Habilita tipos de batida customizados no iDFlex ponto",
            ),
        ),
        migrations.AlterField(
            model_name="systemconfig",
            name="catra_timeout",
            field=models.IntegerField(default=30000, help_text="Timeout da catraca em milissegundos"),
        ),
        migrations.AlterField(
            model_name="systemconfig",
            name="language",
            field=models.CharField(default="pt_BR", help_text="Idioma do sistema", max_length=10),
        ),
    ]
