# Generated by Django 2.0.7 on 2018-09-01 18:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_auto_20180828_2148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingsubscription',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('completed', 'Completed')], default='active', max_length=50, verbose_name='Billing Status'),
        ),
    ]
