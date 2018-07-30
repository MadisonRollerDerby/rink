from django.urls import reverse, resolve
from test_plus.test import TestCase

from .factories import RegistrationEventFactory

from rink.utils.testing import URLTestCase


class TestRegistrationEventURLs(TestCase, URLTestCase):
    event_factory = RegistrationEventFactory

    def setUp(self):
        self.event = self.event_factory()
        self.reverse_kwargs = {'event_slug': self.event.slug}

    def test_event_admin_list_url(self):
        self.check_url('registration:event_admin_list', '/registration/')

    def test_event_admin_create_url(self):
        self.check_url('registration:event_admin_create', '/registration/new')

    def test_event_settings_url(self):
        self.check_url(
            'registration:event_admin_settings',
            '/registration/{}/settings'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_event_invites_url(self):
        self.check_url(
            'registration:event_admin_invites',
            '/registration/{}/invites'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_event_invite_users_url(self):
        self.check_url(
            'registration:event_admin_invite_users',
            '/registration/{}/invite/users'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_event_invite_emails_url(self):
        self.check_url(
            'registration:event_admin_invite_emails',
            '/registration/{}/invite/emails'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_event_invite_emails_url(self):
        self.check_url(
            'registration:event_admin_roster',
            '/registration/{}/roster'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_event_invite_emails_url(self):
        self.check_url(
            'registration:event_admin_billing_periods',
            '/registration/{}/billing'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

