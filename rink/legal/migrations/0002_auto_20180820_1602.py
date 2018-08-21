# Generated by Django 2.0.7 on 2018-08-20 21:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('league', '0001_initial'),
        ('legal', '0001_initial'),
        ('registration', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='legalsignature',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='registration.RegistrationEvent'),
        ),
        migrations.AddField(
            model_name='legalsignature',
            name='league',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='league.League'),
        ),
        migrations.AddField(
            model_name='legalsignature',
            name='registration',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='registration.RegistrationData'),
        ),
        migrations.AddField(
            model_name='legalsignature',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='legaldocument',
            name='league',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='league.League'),
        ),
        migrations.AlterUniqueTogether(
            name='legaldocument',
            unique_together={('slug', 'league')},
        ),
    ]