import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control_id_django_app", "0040_temporaryuserrelease_visita"),
        ("user_django_app", "0020_visitas_end_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitas",
            name="card",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="visitas",
                to="control_id_django_app.card",
            ),
        ),
        migrations.AddField(
            model_name="visitas",
            name="finished_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visitas",
            name="card_removed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
