from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("control_id_django_app", "0040_temporaryuserrelease_visita"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="temporaryuserrelease",
            name="notified_server",
            field=models.ForeignKey(
                blank=True,
                help_text="Servidor/professor que deve receber o e-mail desta liberacao.",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="notified_temporary_user_releases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
