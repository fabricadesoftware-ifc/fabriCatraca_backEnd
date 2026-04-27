from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0026_accesslogs_access_logs_device__cbcf0b_idx"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="card",
            name="devices",
        ),
        migrations.RemoveField(
            model_name="device",
            name="users",
        ),
        migrations.RemoveField(
            model_name="template",
            name="devices",
        ),
    ]
