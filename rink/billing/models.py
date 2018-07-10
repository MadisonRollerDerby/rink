from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


class BillingStatus(models.Model):
    name = models.CharField(
        "Status Name",
        max_length=50,
        help_text = "Example: 'Injured', 'Active', 'Adminisration', 'Social'",
    )

    slug = models.CharField(
        "Status Slug",
        max_length=50,
    )

    league = models.ForeignKey(
        "league.League",
        on_delete=models.CASCADE,
    )

    description = models.CharField(
        "Status Description",
        max_length=250,
        blank = True,
        help_text = "Any details about what this status represents.",
    )

    bill_amount = models.DecimalField(
        "Dues Amount",
        max_digits = 10,
        decimal_places = 2,
        default = 0.00,
        help_text = "Dollar amount that we should bill these users for each billing period.",
    )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('slug', 'league')


class BillingPeriod(models.Model):
    name = models.CharField(
        "Billing Period Name",
        max_length=50,
        help_text = "Example: 'July Dues''",
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        "league.League",
        on_delete=models.CASCADE,
    )

    start_date = models.DateField(
        "Start Date",
        help_text = "First day of this billing period."
    )

    end_date = models.DateField(
        "End Date",
        help_text = "Last day of this billing period."
    )

    invoice_date = models.DateField(
        "Invoice Date",
        help_text = "The date invoices will be sent out for this billing period."
    )

    due_date = models.DateField(
        "Due Date",
        help_text = "The date payments are due. Automatic credit card billing will also occur on this day."
    )

    dues_amounts = models.ManyToManyField(
        'billing.BillingStatus',
        through='BillingPeriodCustomPaymentAmount',
    )

    class Meta:
        verbose_name = "Dues Billing Date"
        verbose_name_plural = "Dues Billing Dates"
        ordering = ["start_date"]

    def __str__(self):
        return "{} - {} to {}".format(
            self.name,
            self.start_date,
            self.end_date,
        )



class BillingPeriodCustomPaymentAmount(models.Model):
    status = models.ForeignKey(
        'billing.BillingStatus',
        on_delete=models.CASCADE,
    )

    dues_amount = models.DecimalField(
        "Custom Dues Amount",
        max_digits=10,
        decimal_places=2,
        help_text = "The amount we should bill a user matching this status for the billing period specified above.",
    )

    period = models.ForeignKey(
        'billing.BillingPeriod',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Custom Dues Billing Amount"
        verbose_name_plural = "Custom Dues Billing Amounts"




#class Payment(models.Model):

#class Invoice(models.Model):



@receiver(pre_save, sender=BillingStatus)
def my_callback(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)

