from django.conf import settings
from django.core import mail
from django.test import TransactionTestCase
from django.utils import timezone
import pytest
from unittest.mock import patch
from unittest import skip

from .factories import (
    BillingPeriodFactory, BillingGroupFactory, BillingGroupMembershipFactory,
)
from .utils import BillingAppTestCase
from billing.models import UserStripeCard, BillingPeriodCustomPaymentAmount
from league.models import League

import stripe
from stripe.error import InvalidRequestError, CardError

stripe.api_key = settings.STRIPE_TEST_SECRET


"""
Here are the valid test Stripe cards:

4242424242424242    tok_visa
4000056655665556    tok_visa_debit
5555555555554444    tok_mastercard
5200828282828210    tok_mastercard_debit
5105105105105100    tok_mastercard_prepaid
378282246310005     tok_amex
6011111111111117    tok_discover
30569309025904      tok_diners
3566002020360505    tok_jcb
6200000000000005    tok_unionpay


The following failures we do check:

4000000000000101
tok_cvcCheckFail
    If a CVC number is provided, the cvc_check fails. If your account
    is blocking payments that fail CVC code validation the charge
    is declined.

4000000000000341
tok_chargeCustomerFail
    Attaching this card to a Customer object succeeds, but attempts 
    to charge the customer fail.

4000000000000002
tok_chargeDeclined
    Charge is declined with a card_declined code.

4000000000009995
tok_chargeDeclinedInsufficientFunds
    Charge is declined with a card_declined code. The decline_code
    attribute is insufficient_funds.

4100000000000019
tok_chargeDeclinedFraudulent
    Results in a charge with a risk level of highest. The charge is
    blocked as it's considered fraudulent.

4000000000000127
tok_chargeDeclinedIncorrectCvc
    Charge is declined with an incorrect_cvc code.

4000000000000069
tok_chargeDeclinedExpiredCard
    Charge is declined with an expired_card code.

4000000000000119
tok_chargeDeclinedProcessingError
    Charge is declined with a processing_error code.

(no token)
4242424242424241
    Charge is declined with an incorrect_number code as the card
    number fails the Luhn check.

4000000000005126
tok_refundFail
    Charge succeeds but refunding a captured charge fails with a 
    failure_reason of expired_or_canceled_card.


-------------------------------------


Here's a list of things we DO NOT check:

4000000000000010
tok_avsFail     
    The address_line1_check and address_zip_check verifications fail.
    If your account is blocking payments that fail ZIP code
    validation the charge is declined.

4000000000000028
tok_avsLine1Fail
    Charge succeeds but the address_line1_check verification fails.

4000000000000036
tok_avsZipFail
    The address_zip_check verification fails. If your account is
    blocking payments that fail ZIP code validation the charge is declined.

4000000000000044
tok_avsUnchecked
    Charge succeeds but the address_zip_check and address_line1_check 
    verifications are both unavailable.

4000000000009235
tok_riskLevelElevated
    Results in a charge with a risk_level of elevated.

"""


# Mock the private key get method for testing purposes
def override_get_stripe_private_key(self):
    return settings.STRIPE_TEST_SECRET

#@pytest.mark.usefixtures("celery_worker")
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

    #@pytest.mark.celery
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

        #self.assertEqual(len(mail.outbox), 1)
        #self.assertIn('{} -- {} Registration for {}'.format(
        #   event2.name, event2.league.name), mail.outbox[1].subject, self.user)

        payment.delete()
        invoice.delete()
        bp.delete()

    def test_charge_stripe_zero_success(self):
        # Create an invoice with a zero balance and pay it.
        # This should be handled as a cash payment.
        bp = BillingPeriodFactory(league=self.league)
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
    
    def test_stripe_cvc_check_fail(self):
        stripe_test_fail_tokens = [
            #('tok_cvcCheckFail', 'charge', 'CVC Check Fail'),
            ('tok_chargeCustomerFail', 'charge', 'Attach to customer succeeds, but charges fail.'),
            ('tok_chargeDeclined', 'attach', 'Charge declined with card_declined code.'),
            ('tok_chargeDeclinedInsufficientFunds', 'attach', 'Charge declined with card_declined and insufficent funds.'),
            ('tok_chargeDeclinedFraudulent', 'charge', 'Fraudulent transaction'),
            ('tok_chargeDeclinedIncorrectCvc', 'attach', 'Wrong CVC code'),
            ('tok_chargeDeclinedExpiredCard', 'attach', 'Expired card'),
            ('tok_chargeDeclinedProcessingError', 'attach', 'Processing error'),
        ]

        for token, expected_error, reason in stripe_test_fail_tokens:
            print(reason)

            if expected_error == "attach":
                with self.assertRaises(CardError):
                    self.usc.update_from_token(token)
                continue
            else:
                self.usc.update_from_token(token)

            self.usc.refresh_from_db()
            bp = BillingPeriodFactory(league=self.league)
            invoice = bp.generate_invoice(user=self.user)

            if expected_error == "charge":
                with self.assertRaises(CardError):
                    payment = self.usc.charge(invoice=invoice)
                continue
            else:
                payment = self.usc.charge(invoice=invoice)

            invoice.delete()
            bp.delete()
    
    def test_full_refund(self):
        self.usc.update_from_token("tok_visa")  # Visa card, successful charge and attach
        self.usc.refresh_from_db()

        bp = BillingPeriodFactory(league=self.league)
        invoice = bp.generate_invoice(user=self.user)
        payment = self.usc.charge(invoice=invoice)

        payment.refund()
        payment.refresh_from_db()
        invoice.refresh_from_db()

        self.assertEqual(invoice.status, 'refunded')
        self.assertEqual(invoice.refunded_amount, payment.amount)
        self.assertTrue(invoice.refund_date)

        self.assertEqual(payment.refund_amount, payment.amount)
        self.assertEqual(payment.refund_date, invoice.refund_date)
        self.assertFalse(payment.refund_reason)

        stripe_payment = stripe.Charge.retrieve(payment.transaction_id)

        self.assertTrue(stripe_payment.refunded)
        self.assertEqual(stripe_payment.refunds[0].amount, int(payment.amount * 100))
        self.assertEqual(stripe_payment.refunds[0].status, "succeeded")

    @skip("Needs to be converted to a webhook https://stripe.com/docs/refunds")
    def test_failed_refund(self):
        self.usc.update_from_token("tok_refundFail")
        self.usc.refresh_from_db()

        bp = BillingPeriodFactory(league=self.league)
        invoice = bp.generate_invoice(user=self.user)
        payment = self.usc.charge(invoice=invoice)

        #with self.assertRaises(CardError):
        payment.refund()

        stripe_payment = stripe.Charge.retrieve(payment.transaction_id)
        self.assertFalse(stripe_payment.refunded)

    """
    def test_send_receipt(self):

    def test_charge_stripe_multiple_invoices(self):

    def test_parital_refund_success(self):

    def test_parital_refund_success(self):

    def test_partial_refund_failure(self):

    def test_already_refunded(self):

    """
