# Generated by Django 2.0.6 on 2018-07-06 04:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('league', '0006_auto_20180705_2311'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='organization',
            options={'ordering': ['name'], 'permissions': (('org_admin', 'Can manage organization settings, create leagues and more.'),)},
        ),
    ]
