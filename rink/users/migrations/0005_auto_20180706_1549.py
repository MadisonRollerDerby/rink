# Generated by Django 2.0.6 on 2018-07-06 20:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20180705_2311'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(blank=True, default=1, on_delete='League', to='league.League'),
        ),
    ]