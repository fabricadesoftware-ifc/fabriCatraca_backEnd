from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_django_app", "0013_alter_user_app_role_alter_user_panel_access_only_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="cpf",
            field=models.CharField(blank=True, max_length=14, null=True),
        ),
    ]
