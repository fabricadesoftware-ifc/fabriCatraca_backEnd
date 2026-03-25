from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0029_releaseaudit"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesslogs",
            name="raw_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
