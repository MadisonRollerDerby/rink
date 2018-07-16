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

    def clean(self):
        # Start date needs to come before End date
        if self.start_date > self.end_date:
            raise ValidationError("End date invalid, should be a date after Start Date. Did you switch start and end dates?")
        # Invoice date needs to come before due date
        if self.invoice_date > self.due_date:
            raise ValidationError("Invoice date needs occur before Due date. We cannot process payments before they are actually billed. Did you swap the invoice and due dates?")



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
        verbose_name = "Billing Period Amount for Group"
        verbose_name_plural = "Billing Period Amounts for Groups"
        ordering = ['group__name']
        unique_together = ['group', 'period']

    def __str__(self):
        return "{} - {} - ${}".format(self.group.name, self.period.name, self.invoice_amount)

    def clean(self):
        if self.invoice_amount < 0:
            raise ValidationError("Invoice amount must be a positive number.")






INVOICE_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('paid', 'Paid'),
    ('canceled', 'Canceled'),
]

class Invoice(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    billing_period = models.ForeignKey(
        'billing.BillingPeriod',
        on_delete=models.CASCADE,
    )

    description = models.CharField(
        "Invoice Description",
        max_length=200,
        blank=True,
    )

    amount_invoiced = models.DecimalField(
        "Amount Invoiced",
        max_digits=10,
        decimal_places=2,
        help_text="Total amount to invoice",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    amount_paid = models.DecimalField(
        "Amount Paid",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount paid on this invoice",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    status = models.CharField(
        "Invoice Status",
        max_length=50,
        choices=INVOICE_STATUS_CHOICES,
        default="unpaid",
    )

    payment = models.ForeignKey(
        'billing.Payment',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    invoice_date = models.DateField(
        "Invoice Date",
        help_text="The date this invoice was sent or generated",
    )

    invoice_date = models.DateField(
        "Due Date",
        help_text="The date this invoice is due for payment or will be collected for auto payment.",
    )

    paid_date = models.DateTimeField(
        "Payment Date",
        help_text="The date this invoice was marked as paid",
        blank=True,
    )

    class Meta:
        unique_together = ['user', 'league', 'billing_period']
        ordering = ['invoice_date']

    def __str__(self):
        #1234 - Billing Period - Event Name - League Name - $AMOUNT (STATUS)
        return "#{} - {} - {} - {} - ${} ({})".format(
            self.pk,
            self.billing_period.name,
            self.billing_period.event.name,
            self.league.name,
            self.invoice_date,
            self.status
        )



class Payment(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    processor = models.CharField(
        "Payment Processor",
        max_length=50,
        help_text="Name of the payment processor, or possibly Cash or Check."
    )

    transaction_id = models.CharField(
        "Transaction ID",
        max_length=100,
        blank=True,
    )

    amount = models.DecimalField(
        "Amount Paid",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount paid for this transaction",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    fee = models.DecimalField(
        "Payment Processor Fee",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total fee paid to process this transaction",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    card_type = models.CharField(
        "Credit/Debit Card Type",
        max_length=50,
        blank=True,
    )

    card_last4 = models.CharField(
        "Credit/Debit Card Last 4 Digits",
        max_length=4,
        blank=True,
    )

    card_expire_month = models.IntegerField(
        "Credit/Debit Card Expiration Month",
        blank=True,
    )

    card_expire_year = models.IntegerField(
        "Credit/Debit Card Expiration Year",
        blank=True,
    )

    payment_date = models.DateTimeField(
        "Payment Date",
    )

    @property
    def get_card(self):
        if not self.card_type:
            return None
        return "{} ending {}, expires {}/{}".format(
            self.card_type,
            self.card_last4,
            self.card_expire_month,
            self.card_expire_year
        )

    def __str__(self):
        # MM/DD/YY - User - Processor - $AMOUNT - Transaction ID - Card Details
        card_details = ""
        if self.get_card:
            card_details = " - {}".self.get_card
        transaction_id = ""
        if self.transaction_id:
            transaction_id = " - {}".format(transaction_id)

        return "{} - {} - {} - ${}{}{}".format(
            self.payment_date.date(),
            self.user,
            self.processor,
            self.payment_amount,
            transaction_id,
            card_details,
        )


class UserPaymentTokenizedCard(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    token = models.CharField(
        "Customer ID at Payment Processor",
        max_length=50,
    )

    card_type = models.CharField(
        "Credit/Debit Card Type",
        max_length=50,
        blank=True,
    )

    card_last4 = models.CharField(
        "Credit/Debit Card Last 4 Digits",
        max_length=4,
        blank=True,
    )

    card_expire_month = models.IntegerField(
        "Credit/Debit Card Expiration Month",
        blank=True,
    )

    card_expire_year = models.IntegerField(
        "Credit/Debit Card Expiration Year",
        blank=True,
    )

    @property 
    def get_card(self):
        if not self.card_type:
            return None
        return "{} ending {}, expires {}/{}".format(
            self.card_type,
            self.card_last4,
            self.card_expire_month,
            self.card_expire_year
        )

    class Meta:
        unique_together = ['user', 'league']



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
