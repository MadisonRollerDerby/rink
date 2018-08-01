from .utils import RegistrationEventTest
from rink.utils.testing import RinkViewTest

from test_plus.test import TestCase


class TestEventAdminList(RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_list.html'
    url = 'registration:event_admin_list'


class TestEventAdminCreate(RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_create.html'
    url = 'registration:event_admin_create'


class TestEventAdminSettings(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_settings.html'
    url = 'registration:event_admin_settings'


class TestEventAdminInvites(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_invites.html'
    url = 'registration:event_admin_invites'


class TestEventAdminInviteUsers(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_invites.html'
    url = 'registration:event_admin_invite_users'


class TestEventAdminInviteEmails(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_invites.html'
    url = 'registration:event_admin_invite_emails'


class TestEventAdminRoster(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_roster.html'
    url = 'registration:event_admin_roster'


class TestEventAdminBillingPeriods(RegistrationEventTest, RinkViewTest, TestCase):
    league_permissions_required = ['league_admin']
    template = 'registration/event_admin_billing_periods.html'
    url = 'registration:event_admin_billing_periods'
