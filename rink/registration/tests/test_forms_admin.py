from django.db.models.signals import pre_save
from django.test import TestCase, SimpleTestCase

from registration.forms_admin import (
    AUTOMATIC_BILLING_CHOICES, RegistrationAdminEventForm, BillingPeriodInlineForm,
    EventInviteEmailForm, EventInviteAjaxForm
)

from billing.tests.factories import BillingGroupFactory
from league.tests.factories import LeagueFactory
from legal.tests.factories import LegalDocumentFactory

from billing.models import BillingGroup, update_default_billing_group_for_league
from rink.utils.signals import temp_disconnect_signal


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

    def test_billing_group_amounts_and_label(self):
        league = LeagueFactory()
        bg = BillingGroupFactory(league=league)
        field_name = 'billinggroup{}'.format(bg.pk)

        form_data = {
            'name': 'Test Form',
            'start_date': '2012-01-01',
            'end_date': '2012-03-31',
        }

        # Check that label is set correctly
        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertEqual(form[field_name].label, "{} Invoice Amount".format(bg.name))

        # Negative numbers should not be accepted
        form_data[field_name] = -99.99
        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertFalse(form.is_valid(), "BillingGroup in  RegistrationAdminEventForm should not be negative")

        # Large numbers should not be accepted
        form_data[field_name] = 100000000000.0
        form = RegistrationAdminEventForm(data=form_data, league=league)
        self.assertFalse(form.is_valid(), "BillingGroup in  RegistrationAdminEventForm should not be negative")

    def test_billing_groups_league_filter(self):
        league1 = LeagueFactory()
        league2 = LeagueFactory()

        bg1 = BillingGroupFactory(league=league1)
        bg2 = BillingGroupFactory(league=league2)

        # Use an unbound form for this
        form = RegistrationAdminEventForm(league=league1)

        # Key for billing group should not be set
        self.assertRaises(KeyError, lambda: form['billinggroup{}'.format(bg2.pk)])

        # The first billing group should be set and the initial value set
        try:
            self.assertEqual(form['billinggroup{}'.format(bg1.pk)].value(), bg1.invoice_amount)
        except KeyError:
            self.fail("Billing Group should have been set for this league.")

    def test_legal_docs_league_Filter(self):
        league1 = LeagueFactory()
        league2 = LeagueFactory()

        legal_form1 = LegalDocumentFactory(league=league1)
        legal_form2 = LegalDocumentFactory(league=league2)

        form = RegistrationAdminEventForm(league=league1)

        # Legal form 1 should be included in form generated for league 1
        self.assertTrue(any(legal_form1.pk == c[0] for c in form.fields['legal_forms'].choices))

        # LEgal form 2 should NOT be included
        self.assertFalse(any(legal_form2.pk == c[0] for c in form.fields['legal_forms'].choices))


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


class TestEventInviteEmailForm(TestCase):
    def test_league_required_argument(self):
        # League is a required argrument for creating this form.
        with self.assertRaises(TypeError):
            form = EventInviteEmailForm(data={})

    def test_event_invite_form_no_data(self):
        league = LeagueFactory()
        # No data, should fail.
        form = EventInviteEmailForm(data={}, league=league)
        self.assertFalse(form.is_valid(), "Form should not be valid with no data.")

    def test_billing_group_league_filter(self):
        league1 = LeagueFactory()
        league2 = LeagueFactory()

        bg1 = BillingGroupFactory(league=league1)
        bg2 = BillingGroupFactory(league=league2)

        form = EventInviteEmailForm(league=league1)

        # First billing group should be included in form
        self.assertTrue(any(bg1.pk == c.data['value'] for c in form['billing_group']))

        # Second billing group should NOT be included
        self.assertFalse(any(bg2.pk == c.data['value'] for c in form['billing_group']))

    def test_default_billing_group_league_selected(self):
        # Test that if a league has a default billing group set it is selected here
        league = LeagueFactory()

        bg1 = BillingGroupFactory(league=league)
        bg2 = BillingGroupFactory(league=league)
        bg3 = BillingGroupFactory(league=league)

        bg2.default_group_for_league = True
        bg2.save()

        default = BillingGroup.objects.filter(league=league, default_group_for_league=True).get()

        # Default group should be selected on the form.
        form = EventInviteEmailForm(league=league)
        self.assertTrue(any(bg2.pk == c.data['value'] and c.data['selected'] for c in form['billing_group']))

        # Introduce some chaos. Change the league to no longer have a default.
        # Temporarily disable signals so we can set the league to not have a default.
        default.default_group_for_league = False
        kwargs = {
            'signal': pre_save,
            'receiver': update_default_billing_group_for_league,
            'sender': BillingGroup,
        }
        with temp_disconnect_signal(**kwargs):
            default.save()

        # There should no longer be a default group set.
        with self.assertRaises(BillingGroup.DoesNotExist):
            BillingGroup.objects.filter(league=league, default_group_for_league=True).get()

        # Try to create the form with no default group set.
        form = EventInviteEmailForm(league=league)

        # Nothing should be marked as selected.
        self.assertFalse(any(bg1.pk == c.data['value'] and c.data['selected'] for c in form['billing_group']))
        self.assertFalse(any(bg2.pk == c.data['value'] and c.data['selected'] for c in form['billing_group']))


class TestEventInviteAjaxForm(SimpleTestCase):
    def test_event_invite_ajax_form(self):
        # No data sent, should fail
        form = EventInviteAjaxForm(data={})
        self.assertFalse(form.is_valid())

        # invite-12345 is valid.
        # user-12345 is also valid.
        # anything else should not be accepted.

        form = EventInviteAjaxForm(data={'user_or_invite_id': 'invite-12345'})
        self.assertTrue(form.is_valid())

        form = EventInviteAjaxForm(data={'user_or_invite_id': 'user-12345'})
        self.assertTrue(form.is_valid())

        form = EventInviteAjaxForm(data={'user_or_invite_id': 'invite-'})
        self.assertFalse(form.is_valid())

        form = EventInviteAjaxForm(data={'user_or_invite_id': 'user-'})
        self.assertFalse(form.is_valid())

        form = EventInviteAjaxForm(data={'user_or_invite_id': 'pumpkin-999'})
        self.assertFalse(form.is_valid())
