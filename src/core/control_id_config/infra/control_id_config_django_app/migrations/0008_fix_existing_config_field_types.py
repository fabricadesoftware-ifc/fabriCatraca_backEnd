from django.db import migrations, models


def _convert_security_log_type_to_boolean(apps, schema_editor):
    table_name = "control_id_config_django_app_securityconfig"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = %s::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) ILIKE %s
            """,
            [table_name, "%log_type%"],
        )
        constraint_names = [row[0] for row in cursor.fetchall()]

        for constraint_name in constraint_names:
            schema_editor.execute(
                f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS "{constraint_name}"'
            )

        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name = 'log_type'
            """,
            [table_name],
        )
        row = cursor.fetchone()

    if not row or row[0] == "boolean":
        return

    schema_editor.execute(
        f"""
        ALTER TABLE {table_name}
        ALTER COLUMN log_type TYPE boolean
        USING CASE
            WHEN log_type IS NULL THEN FALSE
            WHEN log_type::integer = 0 THEN FALSE
            ELSE TRUE
        END
        """
    )


def _convert_security_log_type_to_smallint(apps, schema_editor):
    table_name = "control_id_config_django_app_securityconfig"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name = 'log_type'
            """,
            [table_name],
        )
        row = cursor.fetchone()

    if not row or row[0] == "smallint":
        return

    schema_editor.execute(
        f"""
        ALTER TABLE {table_name}
        ALTER COLUMN log_type TYPE smallint
        USING CASE
            WHEN log_type IS TRUE THEN 1
            ELSE 0
        END
        """
    )


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
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    _convert_security_log_type_to_boolean,
                    _convert_security_log_type_to_smallint,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="securityconfig",
                    name="log_type",
                    field=models.BooleanField(
                        default=False,
                        help_text="Habilita tipos de batida customizados no iDFlex ponto",
                    ),
                ),
            ],
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
