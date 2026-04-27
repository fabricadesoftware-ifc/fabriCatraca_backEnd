from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0042_temporaryuserrelease_notification_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="temporaryuserrelease",
            name="notification_email",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="E-mail que deve receber a notificacao desta liberacao.",
                max_length=254,
            ),
        ),
    ]
