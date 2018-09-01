from django.conf import settings
from django.test import TransactionTestCase
from django.urls import reverse

from datetime import date
from freezegun import freeze_time
import pytest
from unittest.mock import patch

from billing.models import Invoice
from league.models import League

from billing.tasks import generate_invoices, capture_invoices

from billing.tests.factories import BillingGroupFactory
from league.tests.factories import LeagueFactory
from registration.tests.factories import RegistrationEventFactory, RegistrationDataFactory
from rink.utils.testing import copy_model_to_dict
from users.tests.factories import UserFactoryNoPermissions, user_password

#from taskapp.celery import app as celery_app


# Mock the private key get method for testing purposes
def override_get_stripe_private_key(self):
    return settings.STRIPE_TEST_SECRET

@patch.object(League, 'get_stripe_private_key', override_get_stripe_private_key)
class TestAutomaticBilling(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.league = LeagueFactory()
        self.league.stripe_private_key = settings.STRIPE_TEST_SECRET
        self.league.stripe_public_key = settings.STRIPE_TEST_PUBLIC
        self.league.save()

        self.group = BillingGroupFactory(league=self.league)
        self.group.default_group_for_league = True
        self.group.save()

        self.event = RegistrationEventFactory(
            league=self.league,
            start_date=date(2018, 3, 1),
            end_date=date(2018, 6, 30),
        )
        self.billing_periods = self.event.create_monthly_billing_periods()

    def tearDown(self):
        #self.event.delete()
        #self.group.delete()
        #self.league.delete()
        super().tearDown()

    def get_registration_data(self, user):
        registration_data_obj = RegistrationDataFactory(
            invite=None,
            user=user,
            event=self.event,
            organization=self.league.organization,
        )
        registration_data = copy_model_to_dict(registration_data_obj)
        registration_data_obj.delete()

        registration_data['birth_month'] = 11
        registration_data['birth_day'] = 3
        registration_data['birth_year'] = 1987
        registration_data['legal_agree'] = 'checked'
        registration_data['stripe_token'] = 'tok_visa'
        return registration_data

    def test_automatic_invoicing(self):
        freezer = freeze_time("2018-02-20 12:00:01")
        freezer.start()

        user = UserFactoryNoPermissions(league=self.league, organization=self.league.organization)
        self.client.login(username=user.email, password=user_password)

        response = self.client.post(
            reverse('register:show_form', kwargs={'league_slug': self.league.slug, 'event_slug': self.event.slug}),
            self.get_registration_data(user),
            follow=True)

        # Generate invoice should not create an invoice, as the first period
        # should have been paid during the registration process.
        freezer.stop()
        freezer = freeze_time("2018-03-20 12:00:01")
        freezer.start()
        generate_invoices()
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(Invoice.objects.all()[0].status, "paid")
        self.assertEqual(Invoice.objects.all()[0].subscription.status, "active")

        # Invoice should be generated
        freezer.stop()
        freezer = freeze_time("2018-03-22 12:00:01")
        freezer.start()
        generate_invoices()
        capture_invoices()

        self.assertEqual(Invoice.objects.all()[1].status, "unpaid")
        self.assertEqual(Invoice.objects.all()[1].subscription.status, "active")

        # Card should be automatically charged
        freezer.stop()
        freezer = freeze_time("2018-04-01 12:00:01")
        freezer.start()
        capture_invoices()
        freezer.stop()

        invoices = Invoice.objects.all()
        self.assertEqual(invoices.count(), 2)
        self.assertEqual(invoices[1].status, "paid")
        self.assertEqual(Invoice.objects.all()[1].subscription.status, "active")

        freezer = freeze_time("2018-04-22 12:00:01")
        freezer.start()
        generate_invoices()
        capture_invoices()
        freezer.stop()
        self.assertEqual(invoices.count(), 3)
        self.assertEqual(invoices[2].status, "unpaid")
        self.assertEqual(Invoice.objects.all()[1].subscription.status, "active")


        freezer = freeze_time("2018-05-01 12:00:01")
        freezer.start()
        generate_invoices()
        capture_invoices()
        freezer.stop()
        self.assertEqual(invoices.count(), 3)
        self.assertEqual(invoices[2].status, "paid")
        self.assertEqual(Invoice.objects.all()[2].subscription.status, "active")


        freezer = freeze_time("2018-05-22 12:00:01")
        freezer.start()
        generate_invoices()
        capture_invoices()
        freezer.stop()
        self.assertEqual(invoices.count(), 4)
        self.assertEqual(invoices[3].status, "unpaid")
        self.assertEqual(Invoice.objects.all()[3].subscription.status, "complete")


        freezer = freeze_time("2018-06-01 12:00:01")
        freezer.start()
        generate_invoices()
        capture_invoices()
        freezer.stop()
        self.assertEqual(invoices.count(), 4)
        self.assertEqual(invoices[3].status, "paid")
        self.assertEqual(Invoice.objects.all()[3].subscription.status, "complete")