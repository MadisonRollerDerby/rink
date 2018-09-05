# Generated by Django 2.1.1 on 2018-09-05 04:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0006_auto_20180904_2159'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationdata',
            name='parent1_relationship',
            field=models.CharField(blank=True, max_length=100, verbose_name='Relationship'),
        ),
        migrations.AddField(
            model_name='registrationdata',
            name='parent2_relationship',
            field=models.CharField(blank=True, max_length=100, verbose_name='Relationship'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent1_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Email Address'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent1_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent1_phone',
            field=models.CharField(blank=True, max_length=25, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent2_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Email Address'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent2_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='registrationdata',
            name='parent2_phone',
            field=models.CharField(blank=True, max_length=25, verbose_name='Phone Number'),
        ),
    ]
