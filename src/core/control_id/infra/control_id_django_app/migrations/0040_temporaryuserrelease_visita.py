from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_django_app", "0019_user_created_by_visitas"),
        ("control_id_django_app", "0039_data_migration"),
    ]

    operations = [
        migrations.AddField(
            model_name="temporaryuserrelease",
            name="visita",
            field=models.ForeignKey(
                blank=True,
                help_text="Visita relacionada a esta liberacao temporaria, quando aplicavel.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="temporary_user_releases",
                to="user_django_app.visitas",
            ),
        ),
    ]
