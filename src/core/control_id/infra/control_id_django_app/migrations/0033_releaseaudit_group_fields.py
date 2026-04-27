import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control_id_django_app', '0032_temporarygrouprelease'),
    ]

    operations = [
        migrations.AddField(
            model_name='releaseaudit',
            name='temporary_group_release',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='release_audit',
                to='control_id_django_app.temporarygrouprelease',
            ),
        ),
        migrations.AddField(
            model_name='releaseaudit',
            name='target_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='release_audits_targeted',
                to='control_id_django_app.customgroup',
            ),
        ),
        migrations.AddField(
            model_name='releaseaudit',
            name='target_group_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='releaseaudit',
            name='release_type',
            field=models.CharField(
                max_length=40,
                choices=[
                    ('device_event', 'Liberação por evento'),
                    ('single_turn', 'Giro único'),
                    ('scheduled_user_release', 'Liberação agendada'),
                    ('temporary_user_release', 'Liberação temporária'),
                    ('temporary_group_release', 'Liberação de turma'),
                ],
            ),
        ),
    ]
