from django.test import TestCase

from registration.forms_admin import (
    AUTOMATIC_BILLING_CHOICES, RegistrationAdminEventForm, BillingPeriodInlineForm
)

from billing.tests.factories import BillingGroupFactory
from league.tests.factories import LeagueFactory
from legal.tests.factories import LegalDocumentFactory


class TestRegistrationAdminEventForm(TestCase):
    def test_automatic_billing_choices(self):
        choices = ['', 'once', 'monthly']
        for choice in choices:
            self.assertTrue(
                any(choice == c[0] for c in AUTOMATIC_BILLING_CHOICES),
                "Choice '{}'' not in AUTOMATIC_BILLING_CHOICES".format(choice),
            )

    def test_league_required_argument(self):
        # League is a required argrument for creating this form.
        with self.assertRaises(TypeError):
            form = RegistrationAdminEventForm(data={})

    def test_registration_admin_form_no_data(self):
        league = LeagueFactory()
        # No data, should fail.
        form_data = {}
        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertFalse(form.is_valid(), "Form should not be valid with no data.")

    def test_registration_admin_form_minimum_data(self):
        league = LeagueFactory()
        # Minimum data, should validate.
        form_data = {
            'name': 'Test Form',
            'start_date': '2012-01-01',
            'end_date': '2012-03-31',
        }
        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertTrue(form.is_valid(), "Form should be valid with minimum data.")

    def test_registration_admin_form_minimum_data(self):
        league = LeagueFactory()
        legal_forms_ids = []
        for c in range(1, 3):
            legal_form = LegalDocumentFactory(league=league)
            legal_forms_ids.append(legal_form.pk)

        billing_groups = []
        for bg in range(1, 5):
            billing_groups.append(BillingGroupFactory(league=league))

        # Maximum arguments, all of them, everything and then more.
        form_data = {
            'name': 'Test Form',
            'start_date': '2012-01-01',
            'end_date': '2012-03-31',
            'description': 'Test Description of this event',
            'public_registration_open_date': '2011-12-01',
            'public_registration_closes_date': '2011-12-31',
            'invite_expiration_date': '2011-12-31',
            'minimum_registration_age': 18,
            'maximum_registration_age': 25,
            'automatic_billing_dates': 'monthly',
            # Legal forms
            'legal_forms': legal_forms_ids,
            # Billing Status billing amounts
        }
        for billing_group in billing_groups:
            form_data['billinggroup{}'.format(billing_group.pk)] = billing_group.invoice_amount

        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertTrue(form.is_valid(), "RegistrationAdminEventForm should be valid with all data submitted.")


class TestBillingPeriodInlineForm(TestCase):
    def test_billing_period_inline_form_no_data(self):
        form = BillingPeriodInlineForm(data={})
        self.assertFalse(form.is_valid(), "BillingPeriodInlineForm should not be valid with no data sent.")

    def test_billing_period_inline_form_all_fields(self):
        form_data = {
            'name': 'Test Billing Period',
            'start_date': '2018-01-03',
            'end_date': '2018-02-03',
            'invoice_date': '2018-01-03',
            'due_date': '2018-01-04',
        }
        form = BillingPeriodInlineForm(data=form_data)
        self.assertTrue(form.is_valid(), "BillingPeriodInlineForm should be valid with all data submitted.")
