from django.db import models


class BillingStatus(models.Model):

    name = models.CharField(
        "Status Name",
        max_length=50,
        help_text = "Example: 'injured', 'active', 'adminisration', 'social'",
    )

    description = models.CharField(
        "Status Description",
        max_length=250,
        blank = True,
        help_text = "Notes detailing what this Billing Status all entails.",
    )

    dues_amount = models.DecimalField(
        "Dues Amount",
        max_digits = 10,
        decimal_places = 2,
        default = 0.00,
        help_text = "Dollar amount that we should bill these users for each billing period.",
    )

    def __str__(self):
        return self.name


class BillingSession(models.Model):
    class Meta:
        verbose_name = "Billing Session"
        verbose_name_plural = "Billing Sessions"

    name = models.CharField(
        "Session Name",
        max_length = 50,
        help_text = "Name of the session. Keep it simple, examples: 'Fall 2012', 'Summer 2013'")

    def __str__(self):
        return self.name


class BillingPeriod(models.Model):
    class Meta:
        verbose_name = "Dues Billing Date"
        verbose_name_plural = "Dues Billing Dates"
        ordering = ["start_date"]

    def __str__(self):
        return self.session.name + ' - ' + str(self.start_date) + ' to ' + str(self.end_date)

    session = models.ForeignKey(
        "billing.BillingSession",
        help_text = "Select the Session that this billing period is associated with.",
    )

    invoice_date = models.DateField(
        "Invoice Date",
        help_text = "The date that invoices will be emailed out.",
    )

    due_date = models.DateField(
        "Due Date",
        help_text = "The date that payments are due for this billing period. We will attempt to charge credit cards on this date.",
    )

    start_date = models.DateField(
        "Start Date",
        help_text = "Start date for this billing period.",
    )

    end_date = models.DateField(
        "End Date",
        help_text = "End date for this billing period.",
    )

    dues_amounts = models.ManyToManyField(
        SkaterStatus,
        through='SessionCustomPaymentAmount',
    )



"""
" Skate session payment amount
"   Provides a way to handle custom payment amounts for billing peroids
"""
class SessionCustomPaymentAmount(models.Model):
    class Meta:
        verbose_name = "Custom Dues Billing Amount"
        verbose_name_plural = "Custom Dues Billing Amounts"

    status = models.ForeignKey(SkaterStatus)

    dues_amount = models.DecimalField(
        "Custom Dues Amount",
        max_digits=10,
        decimal_places=2,
        help_text = "The amount we should bill a user matching this status for the billing period specified above.",
    )

    schedule = models.ForeignKey(SkateSessionPaymentSchedule)



#class Payment(models.Model):

#class Invoice(models.Model):




