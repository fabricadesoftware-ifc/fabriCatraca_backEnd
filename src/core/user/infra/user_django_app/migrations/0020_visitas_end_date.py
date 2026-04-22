from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_django_app", "0019_user_created_by_visitas"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitas",
            name="end_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
