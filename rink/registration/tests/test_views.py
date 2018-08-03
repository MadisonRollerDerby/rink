from datetime import timedelta
from django.test import LiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from test_plus.test import TestCase

from .factories import (
    RegistrationInviteFactory, RegistrationEventFactory,
    RegistrationDataFactoryMinimumFields, RegistrationDataFactory,
)
from .utils import RegistrationEventTest
from league.tests.factories import InsuranceTypeFactory
from rink.utils.testing import RinkViewTest, RinkViewLiveTest
from users.tests.factories import user_password

from registration.models import RegistrationEvent
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


class TestRegisterBeginPublicURL(RegistrationEventTest, RinkViewTest, TestCase):
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


class TestRegisterRegisterShowFormPublic(RegistrationEventTest, RinkViewTest, TestCase):
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


class TestRegisterRegisterShowFormLoggedIn(RegistrationEventTest, RinkViewLiveTest, LiveServerTestCase):
    # The big kahuna. Test the registration form.
    skip_permissions_tests = True  # test requires a user, but only an unprivileged one
    #template = "registration/register_form.html"
    url = 'register:register_event_uuid'

    dont_quit = True

    def setUp(self):
        super(TestRegisterRegisterShowFormLoggedIn, self).setUp()
        self.user = self.user_factory()
        self.invite = RegistrationInviteFactory(event=self.event, user=self.user)
        self.insurance = InsuranceTypeFactory()

    def tearDown(self):
        super(TestRegisterRegisterShowFormLoggedIn, self).tearDown()
        if self.invite.id:
            self.invite.delete()
        self.user.delete()
        self.insurance.delete()

    def url_kwargs(self):
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
    def test_registration_form_errors(self):
        form = RegistrationDataForm(instance=self.registration_data_factory())

        self.sign_in_to_register()
        self.wd.key_form_fields(form)
        


class TestRegisterRegisterDonePublic(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    url = 'register:done'

    def setUp(self):
        super(TestRegisterRegisterDonePublic, self).setUp()
        self.redirect = '{}?next={}'.format(
            reverse('account_login'),
            reverse('register:done', kwargs={'event_slug': self.event.slug})
        )
