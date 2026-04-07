from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_django_app", "0014_user_cpf"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="start_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Data de inicio de vigencia do acesso.",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="end_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Data de fim de vigencia do acesso.",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_passage_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Horario da ultima passagem registrada na catraca.",
            ),
        ),
    ]
