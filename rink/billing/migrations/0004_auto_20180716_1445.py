# Generated by Django 2.0.6 on 2018-07-16 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_auto_20180716_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpaymenttokenizedcard',
            name='card_last4',
            field=models.CharField(blank=True, max_length=4, verbose_name='Credit/Debit Card Last 4 Digits'),
        ),
    ]
