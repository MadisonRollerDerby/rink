# Generated by Django 2.0.7 on 2018-08-30 04:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationevent',
            name='max_capacity',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum number of signups until registration is closed. Setting zero or blank allows unlimited signups.', null=True, verbose_name='Maximum Event Signups'),
        ),
    ]
