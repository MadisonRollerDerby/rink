# Generated by Django 2.0.8 on 2018-09-04 20:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('league', '0002_auto_20180904_1417'),
    ]

    operations = [
        migrations.AlterField(
            model_name='league',
            name='style_header_font_css',
            field=models.CharField(blank=True, help_text="The font-face CSS to use for branding the league name in the header. Default is 'Lobster, cursive'.", max_length=100, verbose_name='Header Font Google Font CSS Font-Family'),
        ),
    ]