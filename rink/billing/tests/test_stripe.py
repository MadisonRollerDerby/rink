from django.conf import settings
from django.test import TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from .factories import (
    BillingPeriodFactory, BillingGroupFactory, BillingGroupMembershipFactory,
)
from .utils import BillingAppTestCase
from billing.models import UserStripeCard, BillingPeriodCustomPaymentAmount
from league.models import League

import stripe
from stripe.error import InvalidRequestError
stripe.api_key = settings.STRIPE_TEST_SECRET


# Mock the private key get method for testing purposes
def override_get_stripe_private_key(self):
    return settings.STRIPE_TEST_SECRET

@patch.object(League, 'get_stripe_private_key', override_get_stripe_private_key)
class TestUserStripeIntegrationUpdateToken(BillingAppTestCase, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.group = BillingGroupFactory(league=self.league)
        self.membership = BillingGroupMembershipFactory(
            league=self.league,
            user=self.user,
            group=self.group,
        )
        self.usc, created = UserStripeCard.objects.get_or_create(
            user=self.user,
            league=self.league
        )

    def tearDown(self):
        self.membership.delete()
        self.group.delete()
        super().tearDown()

    def test_success(self):
        # Create a new customer on Stripe with a valid profile and attempt to
        # attach the card.
        usc = self.usc
        usc.update_from_token("tok_visa")  # Visa card, successful charge and attach
        usc.refresh_from_db()

        self.assertEqual(usc.card_type, "Visa")
        self.assertEqual(usc.card_last4, "4242")
        self.assertEqual(usc.card_expire_month, timezone.now().month)
        self.assertEqual(usc.card_expire_year, timezone.now().year + 1)
        self.assertTrue(usc.card_last_update_date)

        customer = stripe.Customer.retrieve(usc.customer_id)
        self.assertEqual(customer.email, self.user.email)
        self.assertFalse(customer.description, self.user.legal_name)

        last_update = usc.card_last_update_date
        old_customer_id = usc.customer_id

        # Now update the card with another valid card and ensure fields are updated.
        usc.update_from_token("tok_amex")
        usc.refresh_from_db()

        self.assertEqual(old_customer_id, usc.customer_id)

        customer = stripe.Customer.retrieve(usc.customer_id)
        self.assertEqual(usc.card_type, "American Express")
        self.assertEqual(usc.card_last4, "8431")
        self.assertEqual(usc.card_expire_month, timezone.now().month)
        self.assertEqual(usc.card_expire_year, timezone.now().year + 1)
        self.assertNotEqual(last_update, usc.card_last_update_date)

    def test_fail(self):
        usc, created = UserStripeCard.objects.get_or_create(
            user=self.user,
            league=self.league
        )
        with self.assertRaises(InvalidRequestError):
            usc.update_from_token("tok_a39x8vjdja")

    def test_charge_stripe_success(self):
        usc = self.usc
        usc.update_from_token("tok_visa")  # Visa card, successful charge and attach
        usc.refresh_from_db()

        bp = BillingPeriodFactory(league=self.league)
        invoice = bp.generate_invoice(user=self.user)
        payment = usc.charge(invoice=invoice)

        invoice.refresh_from_db()
        self.assertEqual(payment.amount, invoice.paid_amount)
        self.assertEqual(payment.processor, "stripe")
        self.assertEqual(payment.league.pk, invoice.league.pk)
        self.assertEqual(payment.user.pk, invoice.user.pk)
        self.assertEqual(payment.payment_date, invoice.paid_date)
        self.assertEqual(payment.card_type, usc.card_type)
        self.assertEqual(payment.card_last4, usc.card_last4)
        self.assertEqual(payment.card_expire_month, usc.card_expire_month)
        self.assertEqual(payment.card_expire_year, usc.card_expire_year)
        self.assertTrue(payment.payment_date)
        self.assertEqual(invoice.status, 'paid')

        payment.delete()
        invoice.delete()
        bp.delete()

    def test_charge_stripe_zero_success(self):
        # Create an invoice with a zero balance and pay it.
        # This should be handled as a cash payment.
        bp = BillingPeriodFactory(league=self.league,)
        bpc = BillingPeriodCustomPaymentAmount.objects.create(
            group=self.group,
            period=bp,
            invoice_amount=0
        )
        invoice = bp.generate_invoice(user=self.user)
        payment = self.usc.charge(invoice=invoice)

        invoice.refresh_from_db()
        self.assertEqual(payment.processor, "cash")
        self.assertEqual(payment.amount, 0)
        self.assertFalse(payment.card_type)
        self.assertFalse(payment.card_last4)
        self.assertFalse(payment.card_expire_month)
        self.assertFalse(payment.card_expire_year)

        self.assertEqual(invoice.paid_amount, 0)
        self.assertEqual(invoice.status, 'paid')

        payment.delete()
        invoice.delete()
        bpc.delete()
        bp.delete()


    """

    def test_send_receipt(self):

    def 

    def test_charge_stripe_failures(self):

    def test_charge_stripe_multiple_invoices(self):

    def test_cash_payment(self):

    def test_check_payment(self):

    def test_square_payment(self):

    def test_parital_refund_success(self):

    def test_partial_refund_failure(self):

    def test_full_refund(self):

    def test_already_refunded(self):

    """
