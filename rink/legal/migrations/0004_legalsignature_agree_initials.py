# Generated by Django 2.1.1 on 2018-09-05 03:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legal', '0003_legalsignature_agreed_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='legalsignature',
            name='agree_initials',
            field=models.CharField(blank=True, help_text='If registration form requires user to initial agreeing to the documents, record that here.', max_length=3, verbose_name='Initials'),
        ),
    ]
