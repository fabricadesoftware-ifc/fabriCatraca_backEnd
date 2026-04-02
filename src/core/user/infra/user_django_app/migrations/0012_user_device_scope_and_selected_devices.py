from django.db import migrations, models


def backfill_device_scope(apps, schema_editor):
    User = apps.get_model("user_django_app", "User")
    User.objects.filter(panel_access_only=True).update(device_scope="none")
    User.objects.exclude(panel_access_only=True).update(device_scope="all_active")


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0035_biometriccapturesession"),
        ("user_django_app", "0011_user_deleted_at_user_deleted_by_cascade_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="device_scope",
            field=models.CharField(
                choices=[
                    ("all_active", "Todas as catracas ativas"),
                    ("selected", "Catracas selecionadas"),
                    ("none", "Nao sincronizar com catracas"),
                ],
                default="all_active",
                help_text="Define em quais catracas o usuario deve existir.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="selected_devices",
            field=models.ManyToManyField(
                blank=True,
                help_text="Catracas escolhidas quando o escopo for selecionado.",
                related_name="scoped_users",
                to="control_id_django_app.device",
            ),
        ),
        migrations.RunPython(backfill_device_scope, migrations.RunPython.noop),
    ]
