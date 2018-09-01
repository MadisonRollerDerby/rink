# Generated by Django 2.0.7 on 2018-08-29 02:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('league', '0001_initial'),
        ('billing', '0004_auto_20180827_1120'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='subscription',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='billing.BillingSubscription'),
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together={('user', 'league', 'billing_period', 'subscription')},
        ),
    ]