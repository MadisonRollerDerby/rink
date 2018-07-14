from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver

from decimal import Decimal


class BillingGroup(models.Model):
    name = models.CharField(
        "Status Name",
        max_length=50,
        help_text = "Example: 'Injured', 'Member', 'Adminisration', 'Social'",
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

    invoice_amount = models.DecimalField(
        "Custom Dues Amount",
        max_digits=10,
        decimal_places=2,
        help_text="The amount we should bill a user matching this status for the billing period specified above.",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    default_group_for_league = models.BooleanField(
        "Is Default Billing Group",
        help_text = "If selected, this is the default billing group that new users and events will assign people to.",
        default = False,
    )

    def __str__(self):
        default = ""
        if self.default_group_for_league:
            default = " (DEFAULT)"
        return "{} - {}{}".format(self.league.name, self.name, default)

    class Meta:
        unique_together = ('name', 'league')
        ordering = ['league', 'name']


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
        'billing.BillingGroup',
        through='BillingPeriodCustomPaymentAmount',
    )

    class Meta:
        verbose_name = "Dues Billing Date"
        verbose_name_plural = "Dues Billing Dates"
        ordering = ['league', 'event', 'start_date']

    def __str__(self):
        return "{} - {} to {}".format(
            self.name,
            self.start_date,
            self.end_date,
        )



class BillingPeriodCustomPaymentAmount(models.Model):
    group = models.ForeignKey(
        'billing.BillingGroup',
        on_delete=models.CASCADE,
    )

    invoice_amount = models.DecimalField(
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


@receiver(pre_delete, sender=BillingGroup)
def delete_default_billing_group_for_league(sender, instance, *args, **kwargs):
    if instance.default_group_for_league:
        raise ValidationError("You cannot delete the default Billing Group for a league. Please set another group as the default one first.")

@receiver(pre_save, sender=BillingGroup)
def update_default_billing_group_for_league(sender, instance, *args, **kwargs):
    # Force only one item per league to be set as the default item

    if not instance.league: # not sure why this would happen....
        return

    # First check and see if this is the first billing group in the league.
    # It should be default=True by... default.
    if not BillingGroup.objects.filter(league=instance.league):
        instance.default_group_for_league = True
        return

    # If default_group_for_league is unselected, ignore it.
    # The only way to change it is select a different default.
    if instance.id:
        old_instance = BillingGroup.objects.get(pk=instance.id)
        # Was True, Now False
        if not instance.default_group_for_league and old_instance.default_group_for_league:
            instance.default_group_for_league = True
            return

    if instance.default_group_for_league:
        # True was already set
        if instance.id and old_instance.default_group_for_league:
            return

        all_others = BillingGroup.objects.filter(league=instance.league)
        if instance.id:
            all_others.exclude(pk=instance.id)
        
        all_others.update(default_group_for_league=False)
