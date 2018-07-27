from django.urls import reverse, resolve
from test_plus.test import TestCase

from .factories import UserFactory


class TestUserURLs(TestCase):
    """Test URL patterns for users app."""

    user_factory = UserFactory

    def setUp(self):
        self.user = self.make_user()

    def test_profile_reverse(self):
        # users:profile should resolve to /profile/
        self.assertEqual(reverse('users:profile'), '/users/profile/')

    def test_profile_resolve(self):
        # /profile/ should resolve to users:profile
        self.assertEqual(resolve('/users/profile/').view_name, 'users:profile')
