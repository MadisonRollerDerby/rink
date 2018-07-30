from django.urls import reverse, resolve
from test_plus.test import TestCase

from .factories import UserFactory

from rink.utils.testing import URLTestCase


class TestUserURLs(TestCase, URLTestCase):
    def test_profile_url(self):
        # users:profile should resolve to /profile/
        # /profile/ should resolve to users:profile
        self.check_url('users:profile', '/users/profile/')
