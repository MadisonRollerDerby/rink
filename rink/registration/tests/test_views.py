from datetime import timedelta

from django.core import mail
from django.test import LiveServerTestCase
from django.urls import reverse
from django.utils import timezone

import pytest
from django.test import TestCase, TransactionTestCase

from .factories import (
    RegistrationInviteFactory, RegistrationEventFactory,
    RegistrationDataFactoryMinimumFields, RegistrationDataFactory,
)
from .utils import RegistrationEventTest
from billing.tests.factories import BillingGroupFactory, BillingPeriodFactory
from league.tests.factories import InsuranceTypeFactory
from legal.tests.factories import LegalDocumentFactory
from rink.utils.testing import RinkViewTest, RinkViewLiveTest, copy_model_to_dict
from users.tests.factories import user_password

from registration.models import RegistrationEvent, RegistrationData, RegistrationInvite
from registration.tasks import send_registration_confirmation
from registration.forms import RegistrationDataForm
from users.models import User


class TestRegisterBeginWithUUID(RegistrationEventTest, RinkViewLiveTest, LiveServerTestCase):
    # Tests the RegisterBegin view using the UUID invite entry.
    # This test class also covers many of the facets that also apply to the
    # public entry point in the test class below.
    is_public = True
    url = 'register:register_event_uuid'

    def setUp(self):
        super(TestRegisterBeginWithUUID, self).setUp()
        self.invite = RegistrationInviteFactory(event=self.event)
        self.redirect = reverse('register:create_account', kwargs={'event_slug': self.event.slug})

    def tearDown(self):
        if self.invite.id:
            self.invite.delete()
        self.redirect = None

    def url_kwargs(self):
        return {'invite_key': self.invite.uuid}

    def test_with_no_matching_uuid(self):
        # Should throw a 404
        self.invite.delete()
        response = self.client.get(self.get_url())
        self.assertEquals(response.status_code, 404)

    def test_with_invite_user_not_authenticated(self):
        # Invites attached to users should be redirected to a page to login
        self.invite.user = self.user_factory()
        self.invite.save()
        response = self.client.get(self.get_url(), follow=True)
        self.assertRedirects(response, '{}?next={}'.format(reverse('account_login'), self.get_url()))
        self.assertContains(response, "Please login to register for '{}'".format(self.event.name))
        self.assertTemplateUsed(response, "account/login.html")

    def test_with_invite_user_other_user_logged_in(self):
        self.invite.user = self.user_factory()
        self.invite.save()
        other_user = self.user_factory()
        self.client.login(email=other_user.email, password=user_password)
        response = self.client.get(self.get_url())
        self.assertContains(response, "User Conflict - Please Logout")
        self.assertTemplateUsed(response, "registration/register_error.html")

    def test_registration_invites_expiration(self):
        # Create a user and attach it to the invite to simplify this test
        user = self.user_factory()
        self.invite.user = user
        self.invite.save()
        self.client.login(email=user.email, password=user_password)

        # By default, registration should be open
        response = self.client.get(self.get_url(), follow=True)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register_form.html")
        # Session data should be set
        self.assertEqual(self.client.session['register_event_id'], self.event.pk)
        self.assertEqual(self.client.session['register_invite_id'], self.invite.pk)

        # Mark invites as expired, registration should close
        self.event.invite_expiration_date = timezone.now() - timedelta(days=1)
        self.event.save()
        response = self.client.get(self.get_url(), follow=True)
        self.assertContains(response, "Registration Closed")
        self.assertTemplateUsed(response, "registration/register_error.html")

    def test_create_user_via_invite_uuid(self):
        # Test that when a user is created from an invite, the invite is updated
        # with the user ID.
        email = 'new1@test.com'
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"email": email, "password1": user_password, "password2": user_password})
        self.wd.find_element_by_xpath('//input[@value="Continue Registration"]').click()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.fail("User was not created")

        self.invite.refresh_from_db()
        self.assertEqual(self.invite.user, user)

    def test_create_user_via_invite_uuid_delete_it(self):
        # Test that when a user is created from an invite, but the invite is deleted
        # somehow before attempting to link the user to the invite. They should still
        # be redirected to the registration form.
        email = 'new1@test.com'
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"email": email, "password1": user_password, "password2": user_password})
        self.invite.delete()
        self.wd.find_element_by_xpath('//input[@value="Continue Registration"]').click()

        self.assertTrue(self.wd.current_url.endswith(
            reverse('register:show_form', kwargs={'event_slug': self.event.slug})))


class TestRegisterBeginPublicURL(RegistrationEventTest, RinkViewTest, TransactionTestCase):
    # Tests the RegisterBegin view using the public entry URL.
    is_public = True
    url = 'register:register_event'

    def setUp(self):
        super(TestRegisterBeginPublicURL, self).setUp()
        self.redirect = reverse('register:create_account', kwargs={'event_slug': self.event.slug})

    def test_public_registration_open_close_dates(self):
        # Set open date to 1 days prior and close date 1 day past,
        # Registration should still be open
        self.event.public_registration_open_date = timezone.now() - timedelta(days=1)
        self.event.public_registration_closes_date = timezone.now() + timedelta(days=1)
        self.event.save()
        response = self.client.get(self.get_url(), follow=True)
        self.assertContains(response, "Please create an account to register for '{}'".format(self.event.name))
        self.assertContains(response, "<h2>{} Registration</h2>".format(self.event.name), html=True)
        self.assertContains(response, "<title>{} Registration - {}</title>".format(
            self.event.name, self.league.name), html=True)
        self.assertTemplateUsed(response, "registration/register_create_account.html")

        # Session data should be set
        self.assertEqual(self.client.session['register_event_id'], self.event.pk)
        with self.assertRaises(KeyError):
            self.client.session['register_invite_id']

        # Test changing the open date to the future, it should close registration.
        self.event.public_registration_open_date = timezone.now() + timedelta(days=1)
        self.event.public_registration_closes_date = timezone.now() + timedelta(days=3)
        self.event.save()

        response = self.client.get(self.get_url(), follow=True)
        self.assertContains(response, "Registration Not Quite Open Yet")
        self.assertTemplateUsed(response, "registration/register_error.html")

        # Test changing the close date to teh past, it should also close registration.
        self.event.public_registration_open_date = timezone.now() - timedelta(days=1)
        self.event.public_registration_closes_date = timezone.now() - timedelta(days=3)
        self.event.save()

        response = self.client.get(self.get_url(), follow=True)
        self.assertContains(response, "Registration Closed")
        self.assertTemplateUsed(response, "registration/register_error.html")


class TestRegisterCreateAccount(RegistrationEventTest, RinkViewLiveTest, LiveServerTestCase):
    is_public = True
    template = "registration/register_create_account.html"
    url = 'register:create_account'

    def setUp(self):
        super(TestRegisterCreateAccount, self).setUp()

    def test_create_account_valid(self):
        email = 'testing@rink.com'
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"email": 'testing@rink.com', "password1": user_password, "password2": user_password})
        self.wd.find_element_by_xpath('//input[@value="Continue Registration"]').click()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.fail("User was not created by create user form.")

    def test_form_error_messages_displayed(self):
        # Password is too short
        email = 'testing@rink.com'
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"email": email, "password1": "short", "password2": "short"})
        self.wd.find_element_by_xpath('//input[@value="Continue Registration"]').click()

        self.assertTrue(self.wd.class_contains("invalid-feedback", "This password is too short. It must contain at least 8 characters."))

        # Attempt to create a user with an existing username
        user = self.user_factory()
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"email": user.email, "password1": user_password, "password2": user_password})
        self.wd.find_element_by_xpath('//input[@value="Continue Registration"]').click()

        self.assertTrue(self.wd.class_contains("invalid-feedback", "User with this Email address already exists."))


class TestRegisterRegisterShowFormPublic(RegistrationEventTest, RinkViewTest, TransactionTestCase):
    # Attempt to load the registration form without logging in. Should redirect
    # back to the login page.
    is_public = True
    url = 'register:show_form'

    def setUp(self):
        super(TestRegisterRegisterShowFormPublic, self).setUp()
        self.redirect = '{}?next={}'.format(
            reverse('account_login'),
            reverse('register:show_form', kwargs={'event_slug': self.event.slug})
        )


@pytest.mark.usefixtures("celery_worker")
class TestCanSendRegistrationConfirmEmail(TransactionTestCase):
    def test_celery(self):
        self.assertEqual(len(mail.outbox), 0)
        d = RegistrationDataFactory()
        send_registration_confirmation(registration_data_id=d.pk)
        self.assertEqual(len(mail.outbox), 1)


@pytest.mark.usefixtures("celery_worker")
class TestRegisteShowFormLoggedIn(RegistrationEventTest, RinkViewLiveTest, LiveServerTestCase):
    # The big kahuna. Test the registration form.
    skip_permissions_tests = True  # test requires a user, but only an unprivileged one
    url = 'register:register_event_uuid'

    #dont_quit = True

    def setUp(self):
        super().setUp()
        self.user = self.user_factory()
        self.invite = RegistrationInviteFactory(event=self.event, user=self.user)
        self.insurance = InsuranceTypeFactory()
        self.legal_documents = (
            LegalDocumentFactory(league=self.league),
            LegalDocumentFactory(league=self.league),
            LegalDocumentFactory(league=self.league),
        )
        for doc in self.legal_documents:
            self.event.legal_forms.add(doc)

    def tearDown(self):
        super().tearDown()
        if self.invite and self.invite.id:
            self.invite.delete()
        self.user.delete()
        self.insurance.delete()
        for document in self.legal_documents:
            document.delete()

    def url_kwargs(self):
        if self.invite:
            return {'invite_key': self.invite.uuid}

    # Helper methods for selenium tests.
    def registration_data_factory(self, delete_after_create=True):
        registration_data = RegistrationDataFactory(
            invite=self.invite,
            user=self.user,
            event=self.event,
            organization=self.organization,
            derby_insurance_type=self.insurance,
        )
        if delete_after_create:
            # just using it to generate an instance, kill it.
            registration_data.delete()
        return registration_data

    def sign_in_to_register(self):
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.key_fields({"login": self.user.email, "password": user_password})
        self.wd.find_element_by_xpath("//button[@type='submit' and text()='Sign In']").click()

    def submit_registration_form(self):
        self.wd.find_element_by_xpath('//input[@value="Submit Registration"]').click()

    # Here's some actual tests.
    def test_registration_form_fields_required(self):
        self.sign_in_to_register()

        # Make the form empty and submit it, we should have some errors.
        self.wd.execute_script("$('#payment-form').attr('novalidate', 'novalidate');")
        self.wd.execute_script("$('#id_contact_email').val('');")
        self.submit_registration_form()

        self.assertTrue(self.wd.id_contains("error_1_id_contact_email", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_first_name", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_last_name", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_address1", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_city", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_state", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_zipcode", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_contact_phone", "This field is required."))

        self.assertTrue(self.wd.id_contains("error_1_id_emergency_date_of_birth", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_emergency_contact", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_emergency_phone", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_emergency_relationship", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_emergency_hospital", "This field is required."))
        self.assertTrue(self.wd.id_contains("error_1_id_emergency_allergies", "This field is required."))

        self.assertTrue(self.wd.id_contains("error_legal_document_agree",
            "You must agree to the legal documents below to register. Please contact us if you have any questions."))

    def test_registration_form_duplicate_email(self):
        registration_data = self.registration_data_factory()

        # Create a conflicting user and try to register using that email address
        conflict_user = self.user_factory()
        registration_data_conflict = copy_model_to_dict(registration_data)
        registration_data_conflict['contact_email'] = conflict_user.email
        conflict_form = RegistrationDataForm(
            logged_in_user_id=self.user.pk, data=registration_data_conflict)

        self.sign_in_to_register()

        self.wd.key_form_fields(conflict_form)
        for doc in self.legal_documents:
            self.wd.checkbox("Legal{}".format(doc.pk))
        self.submit_registration_form()

        self.assertTrue(self.wd.xpath_contains("//h4", "Duplicate Email Address"))

    def test_registration_form_valid_fields(self):
        # Now let's fill out the form and submit it.
        # Fill in all the fields and test actually registering someone.
        registration_data = self.registration_data_factory()
        form = RegistrationDataForm(
            logged_in_user_id=self.user.pk, instance=registration_data)

        self.sign_in_to_register()
        self.wd.key_form_fields(form)
        for doc in self.legal_documents:
            self.wd.checkbox("Legal{}".format(doc.pk))
        self.submit_registration_form()

        # We should end up on the successful registration form
        self.assertTrue(self.wd.xpath_contains("//h2", "{} Registration".format(self.event.name)))
        self.assertTrue(self.wd.xpath_contains("//p", "You're all done registering."))

        # User details should have been updated to their user profile
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, registration_data.contact_first_name)
        self.assertEqual(self.user.last_name, registration_data.contact_last_name)
        self.assertEqual(self.user.email, registration_data.contact_email)
        self.assertEqual(self.user.derby_name, registration_data.derby_name)
        self.assertEqual(self.user.derby_number, registration_data.derby_number)
        # User has been appropriately tagged as a member of the league
        self.assertTrue(self.user.has_perm("league_member", self.league))
        # Registration invite has been marked as completed
        self.invite.refresh_from_db()
        self.assertTrue(self.invite.completed_date)
        invite = self.invite
        self.invite = None
        self.url = "register:register_event"

        # Test that the next time this user registers, they will have their details
        # brought back up and can just submit the form.

        event2 = RegistrationEventFactory(league=self.league)
        for doc in self.legal_documents:
            event2.legal_forms.add(doc)

        self._url_kwargs = {'event_slug': event2.slug}
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        for doc in self.legal_documents:
            self.wd.checkbox("Legal{}".format(doc.pk))
        self.wd.find_element_by_xpath('//input[@value="Submit Registration"]').click()

        self.assertTrue(self.wd.xpath_contains("//h2", "{} Registration".format(event2.name)))
        self.assertTrue(self.wd.xpath_contains("//p", "You're all done registering."))

        # Now, if we go back and try and regsiter again, we will get an
        # error message stating we already have registered.
        self.wd.get('%s%s' % (self.live_server_url, self.get_url()))
        self.wd.class_contains("alert-warning", "already registered")

        # User should have two reg data objects they are registered for now
        # These objects should also be relatively equal... relatively. Due to the reuse
        # of the registration data the second time around.
        registration_data_objs = RegistrationData.objects.filter(user=self.user).order_by('id')
        invite1 = RegistrationInvite.objects.get(user=self.user, event=self.event)
        invite2 = RegistrationInvite.objects.get(user=self.user, event=event2)

        self.assertEqual(registration_data_objs.count(), 2)
        for field in registration_data_objs[0]._meta.get_fields():
            try:
                # Skip these fields, as they should be different
                if field.name not in ['id', 'event', 'registration_date', 'legal_forms', 'invite']:
                    self.assertEqual(
                        getattr(registration_data_objs[0], field.name),
                        getattr(registration_data_objs[1], field.name))
                else:
                    self.assertNotEqual(
                        getattr(registration_data_objs[0], field.name),
                        getattr(registration_data_objs[1], field.name))
            except AttributeError:
                pass

        # Registration invites were created and marked as completed.
        self.assertEqual(registration_data_objs[0].invite.pk, invite1.pk)
        self.assertTrue(registration_data_objs[0].invite.completed_date)
        self.assertFalse(registration_data_objs[0].invite.public_registration)
        # This second event actually was created without an invite, it would have
        # been crated during POST save in the view

        self.assertTrue(invite2.public_registration)
        self.assertEqual(invite2.email, self.user.email)
        self.assertEqual(invite2.sent_date, invite2.completed_date)

        # Check that an email was sent for the registration
        # There should now be 2 messages in the inbox since we registred twice.
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('{} -- {} Registration for {}'.format(
            event2.name, event2.league.name), mail.outbox[1].subject, self.user)

        #  Manual clean up
        invite.delete()
        self.url = 'register:register_event_uuid'
        self._url_kwargs = {'event_slug': self.event.slug}

    dont_quit = True
    @pytest.mark.now
    def test_register_with_stripe_success(self):
        group = BillingGroupFactory(league=self.league)
        bp = BillingPeriodFactory(
            league=self.league,
            event=self.event,
            # For the billing period to be selected by get_billing_context in
            # the view, we need to either have a future start date or an end
            # date in the future. Kinda force something like that now.
            start_date=timezone.now() + timedelta(days=30)
        )

        registration_data = self.registration_data_factory()
        form = RegistrationDataForm(
            logged_in_user_id=self.user.pk, instance=registration_data)

        self.sign_in_to_register()
        self.wd.key_form_fields(form)
        for doc in self.legal_documents:
            self.wd.checkbox("Legal{}".format(doc.pk))

        #import pdb; pdb.set_trace()
        self.submit_registration_form()

        group.delete()
        bp.delete()




class TestRegisterRegisterDonePublic(RegistrationEventTest, RinkViewTest, TransactionTestCase):
    is_public = True
    url = 'register:done'

    def setUp(self):
        super(TestRegisterRegisterDonePublic, self).setUp()
        self.redirect = '{}?next={}'.format(
            reverse('account_login'),
            reverse('register:done', kwargs={'event_slug': self.event.slug})
        )
