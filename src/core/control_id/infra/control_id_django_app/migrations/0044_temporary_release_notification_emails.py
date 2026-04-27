from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0043_temporaryuserrelease_notification_email"),
    ]

    operations = [
        migrations.AlterField(
            model_name="temporaryuserrelease",
            name="notification_email",
            field=models.TextField(
                blank=True,
                default="",
                help_text="E-mails que devem receber a notificacao desta liberacao.",
            ),
        ),
        migrations.AddField(
            model_name="temporarygrouprelease",
            name="notification_message",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Mensagem completa do e-mail enviada aos destinatarios.",
            ),
        ),
        migrations.AddField(
            model_name="temporarygrouprelease",
            name="notification_email",
            field=models.TextField(
                blank=True,
                default="",
                help_text="E-mails que devem receber a notificacao desta liberacao.",
            ),
        ),
    ]
