from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_config_django_app", "0006_easy_setup_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="securityconfig",
            name="log_type",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Nivel de log retornado pelo bloco identifier da catraca",
            ),
        ),
        migrations.AddField(
            model_name="securityconfig",
            name="multi_factor_authentication_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Habilita autenticacao multifator no identificador",
            ),
        ),
        migrations.AddField(
            model_name="securityconfig",
            name="verbose_logging_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Habilita logs detalhados do identificador na catraca",
            ),
        ),
    ]
