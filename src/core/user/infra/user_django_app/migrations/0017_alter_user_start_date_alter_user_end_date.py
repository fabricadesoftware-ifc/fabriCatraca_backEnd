from datetime import time

from django.db import migrations, models
from django.utils import timezone


def migrate_validity_to_datetime(apps, schema_editor):
    User = apps.get_model("user_django_app", "User")
    current_timezone = timezone.get_current_timezone()

    for user in User.objects.exclude(start_date__isnull=True):
        start_date = user.start_date
        if start_date is None:
            continue

        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date, current_timezone)

        user.start_date = start_date
        user.save(update_fields=["start_date"])

    for user in User.objects.exclude(end_date__isnull=True):
        end_date = user.end_date
        if end_date is None:
            continue

        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date, current_timezone)

        if (
            end_date.hour == 0
            and end_date.minute == 0
            and end_date.second == 0
            and end_date.microsecond == 0
        ):
            end_date = end_date.replace(
                hour=time.max.hour,
                minute=time.max.minute,
                second=time.max.second,
                microsecond=time.max.microsecond,
            )

        user.end_date = end_date
        user.save(update_fields=["end_date"])


class Migration(migrations.Migration):

    dependencies = [
        ("user_django_app", "0016_alter_user_app_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="start_date",
            field=models.DateTimeField(
                blank=True,
                help_text="Data e hora de inicio de vigencia do acesso.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="end_date",
            field=models.DateTimeField(
                blank=True,
                help_text="Data e hora de fim de vigencia do acesso.",
                null=True,
            ),
        ),
        migrations.RunPython(
            migrate_validity_to_datetime,
            migrations.RunPython.noop,
        ),
    ]
