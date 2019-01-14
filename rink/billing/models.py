from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse

from decimal import Decimal
import stripe
from stripe.error import CardError, InvalidRequestError

from taskapp.celery import app as celery_app


class BillingGroup(models.Model):
    name = models.CharField(
        "Status Name",
        max_length=50,
        help_text="Example: 'Injured', 'Member', 'Adminisration', 'Social'",
    )

    league = models.ForeignKey(
        "league.League",
        on_delete=models.CASCADE,
    )

    description = models.CharField(
        "Status Description",
        max_length=250,
        blank=True,
        help_text="Any details about what this status represents.",
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
        help_text="If selected, this is the default billing group that new users and events will assign people to.",
        default=False,
    )

    def __str__(self):
        default = ""
        if self.default_group_for_league:
            default = " (DEFAULT)"
        return "{} - {}{}".format(self.league.name, self.name, default)

    class Meta:
        unique_together = ('name', 'league')
        ordering = ['league', 'name']

    def get_absolute_url(self):
        return reverse('league:billing_groups_list', kwargs={
            'organization_slug': self.league.organization.slug,
            'slug': self.league.slug,
        })


class BillingPeriod(models.Model):
    name = models.CharField(
        "Billing Period Name",
        max_length=50,
        help_text="Example: 'July Dues''",
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
        help_text="First day of this billing period."
    )

    end_date = models.DateField(
        "End Date",
        help_text="Last day of this billing period."
    )

    invoice_date = models.DateField(
        "Invoice Date",
        help_text="The date invoices will be sent out for this billing period."
    )

    due_date = models.DateField(
        "Due Date",
        help_text="The date payments are due. Automatic credit card billing will also occur on this day."
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
        if not self.start_date or not self.end_date:
            raise ValidationError("Start and End Dates are required, or they are invalid somehow (bad date, extra spaces).")

        if not self.invoice_date:
            raise ValidationError("Invoice date is required, or it invalid somehow (bad date, extra spaces).")

        if not self.due_date:
            raise ValidationError("Due date is required, or it is invalid somehow (bad date, extra spaces).")

        # Start date needs to come before End date
        if self.start_date > self.end_date:
            raise ValidationError("End date invalid, should be a date after Start Date. Did you switch start and end dates?")
        # Invoice date needs to come before due date
        if self.invoice_date > self.due_date:
            raise ValidationError("Invoice date needs occur before Due date. We cannot process payments before they are actually billed. Did you swap the invoice and due dates?")

    def get_invoice_amount(self, billing_group=None, user=None):
        if user and billing_group:
            raise ValueError("Do not pass both billing_group and user to get_invoice_amount")
      
        if user:
            try:
                membership = BillingGroupMembership.objects.get(
                    league=self.league,
                    user=user
                )
            except BillingGroupMembership.DoesNotExist:
                pass
            else:
                billing_group = membership.group

        if billing_group:
            try:
                billing_schedule_obj = BillingPeriodCustomPaymentAmount.objects.get(
                    group=billing_group,
                    period=self,
                )
            except BillingPeriodCustomPaymentAmount.DoesNotExist:
                pass
            else:
                return billing_schedule_obj.invoice_amount

        # If we're still here, use the default amount in the billing_group
        if billing_group:
            return billing_group.invoice_amount

        # If for some reason no group was sent, but we have a billing period
        # use the default group for the league.
        try:
            default_group_for_league = BillingGroup.objects.get(
                league=self.league,
                default_group_for_league=True,
            )
        except BillingGroup.DoesNotExist:
            pass
        else:
            billing_group = default_group_for_league

        if billing_group:
            try:
                billing_schedule_obj = BillingPeriodCustomPaymentAmount.objects.get(
                    group=billing_group,
                    period=self,
                )
            except BillingPeriodCustomPaymentAmount.DoesNotExist:
                pass
            else:
                return billing_schedule_obj.invoice_amount
        
        if billing_group:
            return billing_group.invoice_amount

        # If we are STILL here, that means NO valid billing group set and
        # the billing period/group through table doesn't have an entry.
        # I guess give them a free ride?
        return 0

    def get_invoice_description(self, description="Registration"):
        return "{} {}".format(self.event.name, description)

    def generate_invoice(self, subscription, description="Registration"):
        # returns (object, created_True_or_False)
        return Invoice.objects.get_or_create(
            league=self.league,
            billing_period=self,
            user=subscription.user,
            subscription=subscription,
            defaults={
                'invoice_amount': self.get_invoice_amount(user=subscription.user),
                'invoice_date': timezone.now(),
                'due_date': self.due_date,
                'description': self.get_invoice_description(description),
            }
        )


class BillingGroupMembership(models.Model):
    group = models.ForeignKey(
        'billing.BillingGroup',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return "{} - {} - {}".format(self.league.name, self.group.name, self.user)

    class Meta:
        unique_together = ['user', 'league']


class BillingPeriodCustomPaymentAmount(models.Model):
    group = models.ForeignKey(
        'billing.BillingGroup',
        on_delete=models.CASCADE,
    )

    invoice_amount = models.DecimalField(
        "Custom Dues Amount",
        max_digits=10,
        decimal_places=2,
        help_text="The amount we should bill a user matching this status for the billing period specified above.",
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


BILLING_SUBSCRIPTION_CHOICES = [
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('completed', 'Completed'),
]


class BillingSubscription(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        on_delete=models.CASCADE,
    )

    roster = models.ForeignKey(
        "registration.Roster",
        on_delete=models.SET_NULL,
        null=True,
    )

    status = models.CharField(
        "Billing Status",
        max_length=50,
        choices=BILLING_SUBSCRIPTION_CHOICES,
        default="active",
    )

    create_date = models.DateTimeField(
        "Active Date",
        help_text="The date this subscription was created.",
        auto_now_add=True,
    )

    deactive_date = models.DateTimeField(
        "Deactivate Date",
        help_text="The date this subscription was deactivated.",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-create_date']

    def __str__(self):
        return "{} - {} - {} [{}]".format(
            self.league,
            self.event.name,
            self.user,
            self.status,
        )

    @property
    def active(self):
        if self.status == "active":
            return True
        return False

    def deactivate(self):
        if self.active:
            self.status = 'inactive'
            self.deactive_date = timezone.now()
            self.save()

    def check_completed(self):
        if self.active:
            # Find all invoices related to this subscription
            invoices = Invoice.objects.filter(subscription=self).values_list('billing_period__pk').all()

            # Compare invoices paid to billing periods to find if there are any
            # FUTURE billing periods that will be invoiced
            billing_periods_future_uninvoiced = BillingPeriod.objects.filter(
                event=self.event,
                due_date__gte=timezone.now().date()
            ).exclude(pk__in=invoices).count()

            if billing_periods_future_uninvoiced == 0:
                self.status = 'completed'
                self.deactive_date = timezone.now()
                self.save()


INVOICE_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('paid', 'Paid'),
    ('canceled', 'Canceled'),
    ('refunded', 'Refunded'),
]

INVOICE_STATUS_CLASSES = {
    'unpaid': 'danger',
    'paid': 'success',
    'canceled': 'secondary',
    'refunded': 'warning',
}


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
        null=True,
        blank=True,
    )

    subscription = models.ForeignKey(
        'billing.BillingSubscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    description = models.CharField(
        "Invoice Description",
        max_length=200,
        blank=True,
    )

    invoice_amount = models.DecimalField(
        "Amount Invoiced",
        max_digits=10,
        decimal_places=2,
        help_text="Total amount to invoice",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    paid_amount = models.DecimalField(
        "Amount Paid",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount paid on this invoice",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    refunded_amount = models.DecimalField(
        "Amount Refunded",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount refunded on this invoice",
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
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

    autopay_disabled = models.BooleanField(
        # If for some reason we want automatic payments disabled on an invoice
        # set this to true. Example: registering, and invoice created, but they
        # abandon registration. Don't bill them at a later date.
        "AutoPay Disabled",
        default=False,
    )

    invoice_date = models.DateField(
        "Invoice Date",
        help_text="The date this invoice was generated on.",
    )

    due_date = models.DateField(
        "Due Date",
        help_text="The date this invoice is due for payment or will be collected for auto payment.",
    )

    paid_date = models.DateTimeField(
        "Payment Date",
        help_text="The date this invoice was marked as paid.",
        blank=True,
        null=True,
    )

    refund_date = models.DateTimeField(
        "Refund Date",
        help_text="The date this invoice was refunded.",
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = ['user', 'league', 'billing_period', 'subscription']
        ordering = ['invoice_date']

    def __str__(self):
        #  1234 - Billing Period - Event Name - League Name - $AMOUNT (STATUS)
        description = self.description
        if not self.description:
            description = "(No Description)"
        return "#{} - {} - {} - ${} - {} ({})".format(
            self.pk,
            description,
            self.league.name,
            self.invoice_amount,
            self.invoice_date,
            self.status
        )

    def get_admin_url(self):
        return reverse('roster:admin_billing_invoice', 
            kwargs={'pk': self.user.pk, 'invoice_id': self.pk})

    @property
    def status_class(self):
        return INVOICE_STATUS_CLASSES[self.status]

    def pay(self, amount=None, processor="cash", transaction_id='', payment_date=None):
        if not any(processor in processor_choice for processor_choice in PAYMENT_PROCESSOR_CHOICES):
            raise ValueError("Payment method not in PAYMENT_PROCESSOR_CHOICES: {}".format(processor))

        if not amount:
            amount=self.invoice_amount
        if amount != self.invoice_amount:
            raise ValueError("Payment amount cannot be different than invoice amount. We do not accept partial payments currently. ")

        if not payment_date:
            payment_date = timezone.now()
            
        payment = Payment.objects.create(
            user=self.user,
            league=self.league,
            processor=processor,
            amount=amount,
            payment_date=payment_date,
        )

        self.transaction_id = transaction_id
        self.paid_amount = amount
        self.status = 'paid'
        self.payment = payment
        self.paid_date = payment_date
        self.save()

        return payment

    def is_paid(self):
        if self.status == "paid":
            return True
        return False


PAYMENT_PROCESSOR_CHOICES = [
    ('cash', 'Cash'),
    ('check', 'Check'),
    ('stripe', 'Stripe'),
    ('square', 'Square'),
]


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
        choices=PAYMENT_PROCESSOR_CHOICES,
        default='cash',
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
        null=True,
    )

    card_expire_year = models.IntegerField(
        "Credit/Debit Card Expiration Year",
        blank=True,
        null=True,
    )

    payment_date = models.DateTimeField(
        "Payment Date",
        blank=True,
        null=True,
    )

    refund_date = models.DateTimeField(
        "Refund Date",
        blank=True,
        null=True,
    )

    refund_amount = models.DecimalField(
        "Amount Refunded",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount refunded for this transaction",
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
    )

    refund_reason = models.CharField(
        "Reason for Refund",
        max_length=200,
        blank=True
    )

    def get_card(self):
        if not self.card_type:
            return None
        return "{} ending {}, expires {}/{}".format(
            self.card_type,
            self.card_last4,
            self.card_expire_month,
            self.card_expire_year
        )

    @property
    def is_refunded(self):
        if self.refund_date:
            return True
        else:
            return False

    def __str__(self):
        # MM/DD/YY - User - Processor - $AMOUNT - Transaction ID - Card Details
        card_details = ""
        if self.get_card():
            card_details = " - {}".format(self.get_card())
        transaction_id = ""
        if self.transaction_id:
            transaction_id = " - {}".format(transaction_id)

        return "{} - {} - {} - ${}{}{}".format(
            self.payment_date,
            self.user,
            self.processor,
            self.amount,
            transaction_id,
            card_details,
        )

    def refund(self, amount=None, refund_reason=""):
        if amount:
            if amount > self.amount:
                raise ValueError("Refund amount cannot be larger than the payment amount.")
            if amount <= 0:
                raise ValueError("Refund amount must be larger than zero.")
        else:
            amount = self.amount

        if self.processor == 'stripe':
            stripe.api_key = self.league.get_stripe_private_key()
            refund = stripe.Refund.create(
                charge=self.transaction_id,
                amount=int(amount * 100),
            )

        refund_date = timezone.now()

        self.refund_amount = amount
        self.refund_date = refund_date
        self.refund_reason = refund_reason
        self.save()

        invoices = Invoice.objects.filter(payment=self)
        # If it's a partial refund, this gets complicated
        amount_remaining = amount
        for invoice in invoices:
            invoice.status = 'refunded'
            invoice.refund_date = refund_date

            # Partial refund half-assed attempt
            if amount_remaining < invoice.paid_amount:
                invoice_refund = amount_remaining
                amount_remaining = 0
            else:
                invoice_refund = invoice.paid_amount
                amount_remaining -= invoice.paid_amount

            invoice.refunded_amount = invoice_refund
            invoice.save()


USER_CARD_MAX_FAILURES = 3


class UserStripeCard(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    customer_id = models.CharField(
        "Customer ID at Payment Processor",
        max_length=50,
        blank=True,
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
        null=True,
    )

    card_expire_year = models.IntegerField(
        "Credit/Debit Card Expiration Year",
        blank=True,
        null=True,
    )

    card_last_update_date = models.DateTimeField(
        "Last time credit card was updated",
        blank=True,
        null=True,
    )

    card_last_charge_date = models.DateTimeField(
        "Last time credit card was charged",
        blank=True,
        null=True,
    )

    card_last_fail_date = models.DateTimeField(
        "Last time credit card had a failed charge",
        blank=True,
        null=True,
    )

    card_num_failures = models.IntegerField(
        "Number of times this card has failed",
        default=0,
    )

    @property
    def is_failed(self):
        if self.card_num_failures > USER_CARD_MAX_FAILURES:
            return True
        else:
            return False

    def get_card(self):
        if not self.card_type:
            return "<no card data>"

        failed = ""
        if self.is_failed:
            failed = " (FAILED - declined too many times)"
        return "{} ending {}, expires {}/{}{}".format(
            self.card_type,
            self.card_last4,
            self.card_expire_month,
            self.card_expire_year,
            failed
        )

    def __str__(self):
        return self.get_card()

    class Meta:
        unique_together = ['user', 'league']

    def update_from_token(self, token):
        # Create or update a stripe customer with a new credit card token
        stripe.api_key = self.league.get_stripe_private_key()

        if self.customer_id:
            try:
                customer = stripe.Customer.retrieve(self.customer_id)
            except InvalidRequestError:
                self.customer_id = ""
                self.save()
                customer = None

            if customer:
                if self.user.legal_name == "":
                    customer.description = None
                else:
                    customer.description = self.user.legal_name
                customer.email = self.user.email
                customer.source = token
                try:
                    customer.save()
                except InvalidRequestError:
                    self.customer_id = ""
                    self.save()

        if not self.customer_id:
            # Need to create a stripe customer profile
            customer = stripe.Customer.create(
                description=self.user.legal_name,
                email=self.user.email,
                source=token,
            )
            self.customer_id = customer.id

        try:
            self.card_type = customer.active_card.brand
            self.card_last4 = customer.active_card.last4
            self.card_expire_month = customer.active_card.exp_month
            self.card_expire_year = customer.active_card.exp_year
        except AttributeError:
            pass

        self.card_last_update_date = timezone.now()
        self.card_last_charge_date = None
        self.card_last_fail_date = None
        self.card_num_failures = 0
        self.save()

    def charge(self, invoice=None, invoices=[], send_receipt=True):
        # Charge the customer for an invoice or a list of invoices.
        # Returns a payment object if the payment is successful.
        # send_receipt can be useful in other cases where we  don't want to send
        # yet another email, such as registration.
        if invoice and invoices:
            raise ValueError("You cannot charge both one invoice and multiple invoices at the same time.")

        if not self.customer_id:
            raise ValueError("Please add a credit card below. No credit card is saved on file.")

        if self.card_num_failures >= USER_CARD_MAX_FAILURES:
            raise ValueError("Card has the maximum number of failures ({}) and more charge attempts. User needs to update their card.".format(USER_CARD_MAX_FAILURES))

        if invoice:
            invoices = [invoice, ]

        invoice_numbers = []
        invoice_description = []
        payment_total = 0  # This is dollars * 100, so technically the number of cents

        for invoice in invoices:
            if invoice.user != self.user:
                raise ValueError("You cannot charge an invoice to a card that does not belong to you.")

            invoice_numbers.append('#{}'.format(invoice.pk))
            if invoice.billing_period:
                invoice_description.append("#{} {} - {}".format(
                    invoice.pk, invoice.billing_period.name, invoice.billing_period.event.name))
            else:
                invoice_description.append("#{}".format(invoice.pk))
            payment_total += int(invoice.invoice_amount * 100)

        payment_date = timezone.now()

        if payment_total > 0:
            stripe.api_key = self.league.get_stripe_private_key()
            if not self.customer_id:
                raise ValueError("Cannot charge card, this user does not have a card saved to Stripe.")

            if not invoice_description:
                invoice_description = None

            try:
                charge = stripe.Charge.create(
                    amount=payment_total,
                    currency='usd',
                    customer=self.customer_id,
                    description=', '.join(invoice_description),
                )
            except CardError as e:
                self.card_last_fail_date = timezone.now()
                self.card_num_failures = self.card_num_failures + 1
                self.save()
                raise

            self.card_last_charge_date = timezone.now()
            self.save()

            balance = stripe.BalanceTransaction.retrieve(charge.balance_transaction)

            payment = Payment.objects.create(
                user=self.user,
                league=self.league,
                processor="stripe",
                transaction_id=charge.id,
                amount=Decimal(charge.amount / 100.0),
                fee=Decimal(balance.fee / 100.0),
                card_type=charge.source.brand,
                card_last4=charge.source.last4,
                card_expire_month=charge.source.exp_month,
                card_expire_year=charge.source.exp_year,
                payment_date=payment_date,
            )
        else:
            payment = Payment.objects.create(
                user=self.user,
                league=self.league,
                processor="cash",
                amount=0.00,
                payment_date=payment_date,
            )

        for invoice in invoices:
            invoice.paid_amount = invoice.invoice_amount  # oh, okay?
            invoice.status = 'paid'
            invoice.payment = payment
            invoice.paid_date = payment_date
            invoice.save()

        if payment_total > 0 and send_receipt:
            celery_app.send_task('billing.tasks.email_payment_receipt',
                args=[payment.id], kwargs={})

        return payment


@receiver(pre_delete, sender=BillingGroup)
def delete_default_billing_group_for_league(sender, instance, *args, **kwargs):
    if instance.default_group_for_league and \
        (BillingGroup.objects.exclude(pk=instance.pk).filter(league=instance.league).count() > 0 or \
        BillingPeriodCustomPaymentAmount.objects.filter(group=instance).count() > 0):

        raise ValidationError("You cannot delete the default Billing Group for a league. Please set another group as the default one first.")


@receiver(pre_save, sender=BillingGroup)
def update_default_billing_group_for_league(sender, instance, *args, **kwargs):
    # Force only one item per league to be set as the default item

    if not instance.league:  # not sure why this would happen....
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
