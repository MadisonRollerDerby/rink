from django.urls import reverse, resolve
from test_plus.test import TestCase

from .factories import RegistrationEventFactory, RegistrationInviteFactory

from rink.utils.testing import URLTestCase


class TestRegistrationEventURLs(TestCase, URLTestCase):
    event_factory = RegistrationEventFactory

    def setUp(self):
        self.event = self.event_factory()
        self.reverse_kwargs = {'event_slug': self.event.slug}

    def test_register_invite_with_uuid_url(self):
        invite = RegistrationInviteFactory(event=self.event)
        self.reverse_kwargs['invite_key'] = invite.uuid

        self.check_url(
            'register:register_event_uuid',
            '/register/{}/{}/'.format(self.event.slug, invite.uuid),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_register_event_slug_url(self):
        self.check_url(
            'register:register_event',
            '/register/{}/'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_register_create_account_url(self):
        self.check_url(
            'register:create_account',
            '/register/{}/create-account'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_register_show_form_url(self):
        self.check_url(
            'register:show_form',
            '/register/{}/signup'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )

    def test_register_show_form_url(self):
        self.check_url(
            'register:done',
            '/register/{}/done'.format(self.event.slug),
            reverse_kwargs=self.reverse_kwargs,
        )
