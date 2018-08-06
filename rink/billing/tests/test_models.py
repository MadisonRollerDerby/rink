from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TransactionTestCase
from django.utils import timezone

from datetime import timedelta
from decimal import Decimal

from .factories import (
    BillingGroupFactory, BillingPeriodFactory, RegistrationEventFactory,
)
from league.tests.factories import LeagueFactory
from billing.models import (
    BillingGroup, BillingPeriodCustomPaymentAmount, BillingPeriod,
    BillingPeriodCustomPaymentAmount,
)


class TestBillingGroup(TransactionTestCase):
    def setUp(self):
        self.league = LeagueFactory()

    def tearDown(self):
        if self.league:
            self.league.delete()

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


class TestBillingPeriod(TransactionTestCase):
    def setUp(self):
        self.league = LeagueFactory()

    def tearDown(self):
        if self.league:
            self.league.delete()

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

    def test_get_invoice_amount(self):
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
