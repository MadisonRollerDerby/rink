from django.test import TestCase

from league.tests.factories import LeagueFactory, InsuranceTypeFactory
from legal.tests.factories import LegalDocumentFactory
from registration.forms import (
    RegistrationSignupForm, RegistrationDataForm, LegalDocumentAgreeForm
)
from .factories import RegistrationEventFactory


testing_password = "testing12345"
form_data = {
    'email': 'valid@test.com',
    'password1': testing_password,
    'password2': testing_password,
}


class TestRegistrationSignupForm(TestCase):

    form = RegistrationSignupForm

    def test_signup_form_no_data(self):
        form = self.form(data={})
        self.assertFalse(form.is_valid())

    def test_blank_password(self):
        form = self.form(
            data={
                'email': 'valid@test.com',
                'password1': '',
                'password2': '',
            })
        self.assertFalse(form.is_valid())

    def test_password_validator_works(self):
        # try with a short password, validator should throw ValidationError
        league = LeagueFactory()
        form = self.form(
            data={
                'email': 'valid@test.com',
                'password1': 'test',
                'password2': 'test',
            })
        self.assertFalse(form.is_valid())

    def test_signup_form_valid_data(self):
        form = self.form(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_mismatched_password_inputs(self):
        # Also tests that we are not stripping these inputs.
        form = self.form(
            data={
                'email': 'valid@test.com',
                'password1': '{} '.format(testing_password),  # don't strip the whitespace
                'password2': testing_password,
            })
        self.assertFalse(form.is_valid(), form.errors)

    def test_save_missing_arguments(self):
        form = self.form(data=form_data)
        try:
            form.save()
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("Form save() requires a league to be passed.")

    def test_save_commit(self):
        league = LeagueFactory()
        form = self.form(data=form_data)

        # commit=True should save this by default
        user = form.save(league=league)
        self.assertTrue(user.pk)

        self.assertEqual(user.league, league)
        self.assertEqual(user.organization, league.organization)

    def test_save_no_commit(self):
        league = LeagueFactory()
        form = self.form(data=form_data)

        # commit=False should not save the user
        user = form.save(league=league, commit=False)
        self.assertFalse(user.pk)


class TestRegistrationDataForm(TestCase):
    form = RegistrationDataForm

    required_data = {
        'contact_email': "testing@ytest.com",
        'contact_first_name': 'Test',
        'contact_last_name': 'Tester',
        'contact_address1': '123 Test St',
        'contact_city': 'Test Town',
        'contact_state': 'VA',
        'contact_zipcode': '90210',
        'contact_phone': '4444444444',
        'emergency_date_of_birth': '1928-11-22',
        'emergency_contact': 'Other Test',
        'emergency_phone': '5555555555',
        'emergency_relationship': 'friend who tests',
        'emergency_hospital': 'ouch',
        'emergency_allergies': 'sneezing',     
    }

    optional_data = {
        'derby_name': 'TESTR',
        'derby_number': '1234',
        'derby_insurance_type': '',
        'derby_insurance_number': '12345',
        'derby_pronoun': 'none',
    }

    def setUp(self):
        self.insurance_type = InsuranceTypeFactory()
        self.optional_data['derby_insurance_type'] = self.insurance_type.pk

    def test_placeholder_text(self):
        # Just test that one got set for now. It's probably fine. ...Right?
        form = self.form()
        form['contact_email'].field.widget.attrs['placeholder'] = form['contact_email'].field.label

    def test_stripe_token_field(self):
        form = self.form()
        try:
            self.assertTrue(form['stripe_token'].is_hidden)
        except KeyError:
            self.fail("Stripe token field does not exist")

    def test_form_with_no_data(self):
        form = self.form(data={})
        self.assertFalse(form.is_valid())

    def test_form_with_required_fields(self):
        form = self.form(data=self.required_data)
        self.assertTrue(form.is_valid())

    def test_form_with_all_fields(self):
        form = self.form(data={**self.required_data, **self.optional_data})
        print(form.errors)
        self.assertTrue(form.is_valid())


class TestLegalDocumentAgreeForm(TestCase):
    form = LegalDocumentAgreeForm

    def setUp(self):
        self.event = RegistrationEventFactory()
        self.legal_documents = []
        for count in range(0, 3):
            self.legal_documents.append(LegalDocumentFactory(league=self.event.league))

    def tearDown(self):
        self.league.delete()
        self.legal_documents = []

    def test_legal_document_agree_form_requires_event_arg(self):
        with self.assertRaises(TypeError):
            form = self.form()

    def test_legal_document_agree_form_generates_correct_documents(self):
        # Ensure that we are filtering for other leagues documents
        # and only showing the ones applicable to this league.
        other_league = LeagueFactory()
        other_event = RegistrationEventFactory(league=other_league)
        other_leagues_documents = LegalDocumentFactory(league=other_league)

        form = self.form(league=self.league)
        self.assertEqual(len(form.fields), len(self.legal_documents))

    def test_legal_document_agree_form_none_selected(self):
        form = self.form(event=self.event, data={})
        self.assertFalse(form.is_valid(), form.errors)

    def test_legal_document_agree_form_some_selected(self):
        data = {}
        for count in range(0, len(self.legal_documents) - 1):
            key = 'Legal{}'.format(self.legal_documents[count].pk)
            data[key] = key

        form = self.form(event=self.event, data=data)
        self.assertFalse(form.is_valid(), form.errors)

    def test_legal_document_agree_form_all_selected(self):
        data = {}
        for count in range(0, len(self.legal_documents)):
            key = 'Legal{}'.format(self.legal_documents[count].pk)
            data[key] = key

        form = self.form(event=self.event, data=data)
        self.assertTrue(form.is_valid(), form.errors)  
