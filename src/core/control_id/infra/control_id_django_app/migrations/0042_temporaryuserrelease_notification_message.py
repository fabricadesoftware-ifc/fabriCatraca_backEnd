from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("control_id_django_app", "0041_temporaryuserrelease_notified_server"),
    ]

    operations = [
        migrations.AddField(
            model_name="temporaryuserrelease",
            name="notification_message",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Texto complementar editavel para o e-mail enviado ao servidor.",
            ),
        ),
    ]
