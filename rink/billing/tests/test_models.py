from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TransactionTestCase
from django.utils import timezone

from datetime import timedelta
from decimal import Decimal

from .factories import (
    BillingGroupFactory, BillingPeriodFactory, RegistrationEventFactory,
    PaymentFactory, InvoiceFactory, PaymentFactoryWithCard,
    PaymentFactoryWithRefund, UserStripeCardFactory, BillingGroupMembershipFactory,
)
from .utils import BillingAppTestCase
from league.tests.factories import LeagueFactory
from billing.models import (
    BillingGroup, BillingPeriodCustomPaymentAmount, BillingPeriod,
    BillingPeriodCustomPaymentAmount, Invoice, Payment, INVOICE_STATUS_CHOICES,
    UserStripeCard, BillingGroupMembership, PAYMENT_PROCESSOR_CHOICES
)


class TestBillingGroup(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        with self.assertRaises(AttributeError):
            BillingGroup().save()

        with self.assertRaises(IntegrityError):
            BillingGroup(
                league=self.league,
            ).save()

        bg = BillingGroup(
            league=self.league,
            invoice_amount=5.00,
        ).save()

    def test_all_fields(self):
        bg = BillingGroup(
            name="Test Billing Group",
            league=self.league,
            description="Test description of this here group.",
            invoice_amount=5.55,
            default_group_for_league=True,
        ).save()

    def test_deleting_changing_billing_group(self):
        billing_period = BillingPeriodFactory(league=self.league)

        group0 = BillingGroupFactory(league=self.league, default_group_for_league=False)
        self.assertTrue(group0.default_group_for_league)
        group0.delete()

        group1 = BillingGroupFactory(league=self.league, default_group_for_league=True)
        group2 = BillingGroupFactory(league=self.league, default_group_for_league=False)
        with self.assertRaises(ValidationError):
            group1.delete()

        group2.default_group_for_league = True
        group2.save()

        group1.refresh_from_db()
        group2.refresh_from_db()

        self.assertFalse(group1.default_group_for_league)
        self.assertTrue(group2.default_group_for_league)

        group3 = BillingGroupFactory(league=self.league, default_group_for_league=True)

        group1.refresh_from_db()
        group2.refresh_from_db()
        group3.refresh_from_db()

        self.assertFalse(group1.default_group_for_league)
        self.assertFalse(group2.default_group_for_league)
        self.assertTrue(group3.default_group_for_league)

        group1.delete()

        # Cannot delete a default billing group with a custom period attached.
        bpc1 = BillingPeriodCustomPaymentAmount(
            group=group3,
            invoice_amount=10.00,
            period=billing_period
        ).save()

        group2.delete()
        with self.assertRaises(ValidationError):
            group3.delete()

        # OK, this is a type of django bug we can maybe solve someday.
        # group3.delete() above actually deletes bpc1 before the pre_delete signal
        # fires. Object is still in the database but bcp1 gets hosed.
        BillingPeriodCustomPaymentAmount.objects.all().delete()
        #bpc1.delete()
        group3.delete()

    def test_str(self):
        group = BillingGroupFactory(league=self.league, default_group_for_league=True)
        other_group = BillingGroupFactory(league=self.league, default_group_for_league=False)

        self.assertEqual(
            str(group),
            "{} - {}{}".format(self.league.name, group.name, " (DEFAULT)"),
        )

        other_group.default_group_for_league = True
        other_group.save()
        group.refresh_from_db()

        self.assertEqual(
            str(group),
            "{} - {}".format(self.league.name, group.name),
        )

        group.delete()
        other_group.delete()

    def test_unique_together(self):
        league2 = LeagueFactory()

        group1 = BillingGroupFactory(name="Taco Tuesday", league=self.league)
        group2 = BillingGroupFactory(name="Taco Tuesday", league=league2)

        self.assertNotEqual(group1.league, group2.league)
        self.assertTrue(group1.default_group_for_league)
        self.assertTrue(group2.default_group_for_league)

        with self.assertRaises(IntegrityError):
            BillingGroupFactory(name="Taco Tuesday", league=league2)

        group1.delete()
        group2.delete()


class TestBillingGroupMembership(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        bg = BillingGroupFactory(league=self.league)

        with self.assertRaises(IntegrityError):
            BillingGroupMembership().save()

        bgm = BillingGroupMembership.objects.create(
            user=self.user,
            league=self.league,
            group=bg,
        )
        bgm.delete()
        bg.delete()

    def test_unique_together(self):
        bg = BillingGroupFactory(league=self.league)

        bgm = BillingGroupMembership.objects.create(
            user=self.user,
            league=self.league,
            group=bg,
        )

        with self.assertRaises(IntegrityError):
            bgm = BillingGroupMembership.objects.create(
                user=self.user,
                league=self.league,
                group=bg,
            )

        bgm.delete()
        bg.delete()

    def test_str(self):
        bg = BillingGroupFactory(league=self.league)

        bgm = BillingGroupMembership.objects.create(
            user=self.user,
            league=self.league,
            group=bg,
        )

        self.assertEqual(
            str(bgm),
            "{} - {} - {}".format(self.league.name, bg.name, self.user),
        )

        bgm.delete()
        bg.delete()


class TestBillingPeriod(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            BillingPeriod().save()

        BillingPeriod.objects.create(
            league=self.league,
            event=RegistrationEventFactory(league=self.league),
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() - timedelta(days=15),
            invoice_date=timezone.now(),
            due_date=timezone.now()
        )

    def test_get_invoice_amount_invalid(self):
        billing_period = BillingPeriodFactory(league=self.league)
        billing_group = BillingGroupFactory(league=self.league)
        with self.assertRaises(ValueError):
            billing_period.get_invoice_amount(billing_group=billing_group,
                user=self.user)

    def test_get_invoice_amount_user(self):
        billing_period = BillingPeriodFactory(league=self.league)

        # 1) Test without a valid billing group attached to the user.
        # This should return zero.
        self.assertEqual(billing_period.get_invoice_amount(user=self.user), 0)

        # 2) Attach a billing group to the user.
        # The second billing group should be the non-default one.
        billing_group1 = BillingGroupFactory(league=self.league)
        billing_group2 = BillingGroupFactory(league=self.league)
        self.assertTrue(billing_group1.default_group_for_league)
        self.assertFalse(billing_group2.default_group_for_league)
        self.assertNotEqual(billing_group1.invoice_amount, billing_group2.invoice_amount)

        membership = BillingGroupMembershipFactory(
            league=self.league,
            user=self.user,
            group=billing_group2,
        )

        self.assertEqual(
            billing_period.get_invoice_amount(user=self.user),
            billing_group2.invoice_amount)

        billing_group2.delete()
        billing_group1.delete()
        # The rest of the methods tests are the same as below and covered there.

    def test_get_invoice_amount_billing_group(self):
        billing_period = BillingPeriodFactory(league=self.league)

        # Working backwards to test the method. Here we go:

        # 1) Test without passing a billing group and nothing setup.
        self.assertEqual(billing_period.get_invoice_amount(), 0)

        # 2) Now set a default billing group for this league
        billing_group1 = BillingGroupFactory(league=self.league, default_group_for_league=True)
        billing_group2 = BillingGroupFactory(league=self.league, default_group_for_league=False)

        self.assertEqual(billing_period.get_invoice_amount(), billing_group1.invoice_amount)

        # 3) Next, pass a billing group that does not have a custom payment amount
        # setup for this billing period.
        self.assertEqual(
            billing_period.get_invoice_amount(billing_group=billing_group2),
            billing_group2.invoice_amount
        )

        # 4) Last, create a custom payment amount for this billing group and billing
        # period.
        bpc = BillingPeriodCustomPaymentAmount.objects.create(
            group=billing_group2,
            period=billing_period,
            invoice_amount=9999.98,
        )
        self.assertEqual(
            billing_period.get_invoice_amount(billing_group=billing_group2),
            round(Decimal(bpc.invoice_amount), 2)
        )
        self.assertEqual(
            billing_period.get_invoice_amount(billing_group=billing_group1),
            round(Decimal(billing_group1.invoice_amount), 2)
        )

        bpc.delete()
        billing_group2.delete()
        billing_group1.delete()

    def test_get_invoice_description(self):
        # Only one billing period in the event
        billing_period1 = BillingPeriodFactory(league=self.league)
        self.assertEqual(
            billing_period1.get_invoice_description(),
            "{} Registration".format(billing_period1.event.name)
        )

        # Multiple billing periods in the event, customize description.
        billing_period2 = BillingPeriodFactory(
            league=self.league,
            event=billing_period1.event)
        self.assertEqual(
            billing_period1.get_invoice_description(),
            "{} Dues / Registration".format(billing_period1.name),
        )
        self.assertEqual(
            billing_period2.get_invoice_description(),
            "{} Dues / Registration".format(billing_period2.name),
        )
        self.assertNotEqual(
            billing_period1.get_invoice_description(),
            billing_period2.get_invoice_description(),
        )

    def test_generate_invoice(self):
        # Generate invoice either creates or returns an existing invoice
        # for the specified user .
        billing_period = BillingPeriodFactory(league=self.league)
        invoice, created = billing_period.generate_invoice(self.user)

        self.assertEqual(invoice.league, self.league)
        self.assertEqual(invoice.billing_period, billing_period)
        self.assertEqual(invoice.user, self.user)
        self.assertEqual(invoice.invoice_amount,
            billing_period.get_invoice_amount(user=self.user))
        self.assertTrue(invoice.invoice_date)
        self.assertEqual(invoice.due_date, billing_period.due_date)
        self.assertEqual(invoice.description,
            billing_period.get_invoice_description())

        invoice_again, created = billing_period.generate_invoice(self.user)
        self.assertEqual(invoice.pk, invoice_again.pk)


class TestInvoiceModel(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            Invoice.objects.create()

        invoice_minimum = Invoice.objects.create(
            user=self.user,
            league=self.league,
            billing_period=BillingPeriodFactory(league=self.league),
            description="Test description",
            invoice_amount=40.00,
            invoice_date=timezone.now(),
            due_date=timezone.now(),
        )
        self.assertEqual(invoice_minimum.status, 'unpaid')
        self.assertFalse(invoice_minimum.autopay_disabled)

        Invoice.objects.create(
            user=self.user,
            league=self.league,
            billing_period=BillingPeriodFactory(league=self.league),
            description="Test description",
            invoice_amount=40.00,
            paid_amount=40.00,
            refunded_amount=40.00,
            status='refunded',
            payment=PaymentFactory(user=self.user, amount=40.00),
            autopay_disabled=True,
            invoice_date=timezone.now(),
            due_date=timezone.now(),
            paid_date=timezone.now(),
            refund_date=timezone.now(),
        )

    def test_staus_choices(self):
        self.assertIn(('unpaid', 'Unpaid'), INVOICE_STATUS_CHOICES)
        self.assertIn(('paid', 'Paid'), INVOICE_STATUS_CHOICES)
        self.assertIn(('canceled', 'Canceled'), INVOICE_STATUS_CHOICES)
        self.assertIn(('refunded', 'Refunded'), INVOICE_STATUS_CHOICES)

    def test_unique_together(self):
        bp = BillingPeriodFactory(league=self.league)
        invoice1 = InvoiceFactory(
            billing_period=bp,
            league=self.league,
            user=self.user,
        )
        with self.assertRaises(IntegrityError):
            InvoiceFactory(
                billing_period=bp,
                league=self.league,
                user=self.user,
            )

        invoice1.delete()

    def test_is_paid(self):
        invoice = InvoiceFactory(
            billing_period=BillingPeriodFactory(league=self.league))
        self.assertFalse(invoice.is_paid())

        invoice.status = 'paid'
        invoice.save()
        self.assertTrue(invoice.is_paid())

    def test_pay(self):
        billing_period = BillingPeriodFactory(league=self.league)
        for processor_code, processor_description in PAYMENT_PROCESSOR_CHOICES:
            invoice = InvoiceFactory(billing_period=billing_period)
            payment = invoice.pay(processor=processor_code)

            self.assertEqual(payment.processor, processor_code)
            self.assertEqual(payment.user, invoice.user)
            self.assertEqual(payment.amount, invoice.invoice_amount)
            self.assertEqual(payment.payment_date, invoice.paid_date)
            self.assertEqual(invoice.status, 'paid')
            self.assertEqual(invoice.payment.pk, payment.pk)

            payment.delete()
            invoice.delete()

        # Test with specifying the amount
        invoice = InvoiceFactory(billing_period=billing_period)
        payment = invoice.pay(processor=processor_code, amount=invoice.invoice_amount)
        payment.delete()
        invoice.delete()
        billing_period.delete()

    def test_pay_invalid(self):
        billing_period = BillingPeriodFactory(league=self.league)
        invoice = InvoiceFactory(billing_period=billing_period)
        with self.assertRaises(ValueError):
            invoice.pay(processor="invalid")
        with self.assertRaises(ValueError):
            invoice.pay(processor="cash", amount=-1.00)
        invoice.delete()
        billing_period.delete()


class TestPaymentModel(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            Payment.objects.create()

        payment_minimum = Payment.objects.create(
            user=self.user,
            league=self.league,
        )

        payment_all_fields = Payment.objects.create(
            user=self.user,
            league=self.league,
            processor="stripe",
            transaction_id="#1234",
            amount=99.99,
            fee=1.11,
            card_type="visa",
            card_last4="1234",
            card_expire_month=12,
            card_expire_year=2017,
            payment_date=timezone.now(),
            refund_date=timezone.now(),
            refund_amount=99.99,
            refund_reason="no pie",
        )

        payment_all_fields.delete()
        payment_minimum.delete()

    def test_get_card(self):
        payment = PaymentFactory()
        self.assertFalse(payment.get_card())
        payment.delete()

        payment = PaymentFactoryWithCard()
        self.assertEqual(
            payment.get_card(),
            "{} ending {}, expires {}/{}".format(
                payment.card_type,
                payment.card_last4,
                payment.card_expire_month,
                payment.card_expire_year))
        payment.delete()

    def test_is_refunded(self):
        payment = PaymentFactory()
        self.assertFalse(payment.is_refunded)
        payment.delete()

        payment = PaymentFactoryWithCard()
        self.assertFalse(payment.is_refunded)
        payment.delete()

        payment = PaymentFactoryWithRefund()
        self.assertTrue(payment.is_refunded)
        payment.delete()

    def test_payment_processor_choices(self):
        self.assertIn(('cash', 'Cash'), PAYMENT_PROCESSOR_CHOICES)
        self.assertIn(('check', 'Check'), PAYMENT_PROCESSOR_CHOICES)
        self.assertIn(('stripe', 'Stripe'), PAYMENT_PROCESSOR_CHOICES)
        self.assertIn(('square', 'Square'), PAYMENT_PROCESSOR_CHOICES)


class TestUserStripeCardModel(BillingAppTestCase, TransactionTestCase):
    def test_required_fields(self):
        with self.assertRaises(IntegrityError):
            usc = UserStripeCard.objects.create()

        usc = UserStripeCard.objects.create(
            user=self.user,
            league=self.league,
        )
        usc.delete()

        usc = UserStripeCard.objects.create(
            user=self.user,
            league=self.league,
            customer_id="cus_12345zxvf",
            card_type="visa",
            card_last4="1234",
            card_expire_month=12,
            card_expire_year=2019,
            card_last_update_date=timezone.now(),
            card_last_charge_date=timezone.now(),
            card_last_fail_date=timezone.now(),
        )
        usc.delete()

    def test_unique_together(self):
        usc = UserStripeCard.objects.create(
            user=self.user,
            league=self.league,
        )

        with self.assertRaises(IntegrityError):
            usc = UserStripeCard.objects.create(
                user=self.user,
                league=self.league,
            )

    def test_get_card(self):
        usc = UserStripeCard.objects.create(
            user=self.user,
            league=self.league,
        )
        self.assertEqual(usc.get_card(), "<no card data>")
        usc.delete()

        usc = UserStripeCardFactory()
        self.assertEqual(
            usc.get_card(),
            "{} ending {}, expires {}/{}".format(
                usc.card_type,
                usc.card_last4,
                usc.card_expire_month,
                usc.card_expire_year))

        self.assertEqual(usc.get_card(), str(usc))
        usc.delete()
