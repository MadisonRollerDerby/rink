from test_plus.test import TestCase

from .factories import UserFactory


class TestUser(TestCase):

    user_factory = UserFactory

    def setUp(self):
        self.user = self.make_user()

    def test__str__(self):
        self.assertEqual(
            self.user.__str__(),
            self.user.email  # This is the default email for self.make_user()
        )

    def test_get_absolute_url(self):
        self.assertEqual(
            self.user.get_absolute_url(),
            '/users/{}/'.format(self.user.id)
        )
