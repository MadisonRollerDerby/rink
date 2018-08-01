from django.urls import reverse
from test_plus.test import TestCase

from .factories import RegistrationInviteFactory
from .utils import RegistrationEventTest
from rink.utils.testing import RinkViewTest
from users.tests.factories import UserFactory, user_password


class TestRegisterBeginWithUUID(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    url = 'register:register_event_uuid'

    def setUp(self):
        super(TestRegisterBeginWithUUID, self).setUp()
        self.invite = RegistrationInviteFactory()
        self.redirect = reverse('register:create_account', kwargs={'event_slug': self.event.slug})

    def url_kwargs(self):
        return {'invite_key': self.invite.uuid}


class TestRegisterBegin(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    url = 'register:register_event'

    def setUp(self):
        super(TestRegisterBegin, self).setUp()
        self.redirect = reverse('register:create_account', kwargs={'event_slug': self.event.slug})

    def test_template_contents(self):
        response = self.client.get(self._get_url(), follow=True)
        self.assertContains(response, "Please create an account to register for '{}'".format(self.event.name))
        self.assertContains(response, "<h2>{} Registration</h2>".format(self.event.name), html=True)
        self.assertContains(response, "<title>{} Registration - {}</title>".format(self.event.name, self.league.name), html=True)


class TestRegisterCreateAccount(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    template = "registration/register_create_account.html"
    url = 'register:create_account'


class TestRegisterRegisterShowFormPublic(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    url = 'register:show_form'

    def setUp(self):
        super(TestRegisterRegisterShowFormPublic, self).setUp()
        self.redirect = '{}?next={}'.format(
            reverse('account_login'),
            reverse('register:show_form', kwargs={'event_slug': self.event.slug})
        )


class TestRegisterRegisterShowFormLoggedIn(RegistrationEventTest, RinkViewTest, TestCase):
    skip_permissions_tests = True  # test requires a user, but only an unprivileged one
    template = "registration/register_form.html"
    url = 'register:show_form'


class TestRegisterRegisterDonePublic(RegistrationEventTest, RinkViewTest, TestCase):
    is_public = True
    url = 'register:done'

    def setUp(self):
        super(TestRegisterRegisterDonePublic, self).setUp()
        self.redirect = '{}?next={}'.format(
            reverse('account_login'),
            reverse('register:done', kwargs={'event_slug': self.event.slug})
        )
