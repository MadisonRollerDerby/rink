# Generated by Django 2.1.1 on 2019-01-15 02:27

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_auto_20180906_2304'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingperiodcustompaymentamount',
            name='invoice_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='The amount we should bill a user matching this status for the billing period specified above.', max_digits=10, verbose_name='Custom Dues Amount'),
        ),
    ]