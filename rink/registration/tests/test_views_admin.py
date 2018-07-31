from django.core import mail
from django.test import RequestFactory


from test_plus.test import TestCase

from registration import views_admin
from rink.utils.testing import RinkViewTest

from registration.tests.factories import RegistrationEventFactory


class RegistrationEventTest(object):
    def setUp(self):
        super(RegistrationEventTest, self).setUp()
        try:
            self.event
        except AttributeError:
            self.event = RegistrationEventFactory(league=self.league)
            self.url_kwargs = {'event_slug': self.event.slug}


class TestEventAdminList(RinkViewTest, TestCase):
    league_perms_required = ['league_admin']
    template = 'registration/event_admin_list.html'
    url = 'registration:event_admin_list'


class TestEventAdminCreate(RinkViewTest, TestCase):
    league_perms_required = ['league_admin']
    template = 'registration/event_admin_create.html'
    url = 'registration:event_admin_create'


class TestEventAdminSettings(RegistrationEventTest, RinkViewTest, TestCase):
    league_perms_required = ['league_admin']
    template = 'registration/event_admin_settings.html'
    url = 'registration:event_admin_settings'


"""
class TestEventAdminInvites(RinkViewTest, TestCase):
    league_perms_required = ['league_admin']
    template = 'registration/event_admin_settings.html'

    def setUp(self):
        super(RinkViewTest, self).setUp()
        super(TestCase, self).setUp()
        self.event = RegistrationEvent(league=self.league)
        self.url = reverse('registration:event_admin_invites', kwargs={'event_slug': 'self.event.slug'})
"""
