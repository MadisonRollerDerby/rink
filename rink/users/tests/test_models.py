from django.db.utils import DataError
from django.db import transaction
from test_plus.test import TestCase


from .factories import UserFactory, SuperUserFactory


class TestSuperUser(TestCase):
    user_factory = SuperUserFactory

    def setUp(self):
        self.user = self.make_user()

    def test_is_staff(self):
        self.assertTrue(self.user.is_staff)



class TestUser(TestCase):

    user_factory = UserFactory

    def setUp(self):
        self.user = self.make_user()

    def test__str__(self):
        # Only email address is set
        self.assertEqual(
            self.user.__str__(),
            self.user.email 
        )

        # Now let's set a first name
        self.user.first_name = "FIRST"
        self.assertEqual(
            self.user.__str__(),
            self.user.first_name
        )

        # Now let's only set a last name
        self.user.first_name = None
        self.user.last_name = "LAST"
        self.assertEqual(
            self.user.__str__(),
            self.user.last_name
        )

        # Now let's set both names
        self.user.first_name = "FIRST"
        self.user.last_name = "LAST"
        self.assertEqual(
            self.user.__str__(),
            "FIRST LAST"
        )

        # OK, now set a derby name and both first and last are still set.
        self.user.first_name = "FIRST"
        self.user.last_name = "LAST"
        self.user.derby_name = "DERBY NAME"
        self.assertEqual(
            self.user.__str__(),
            "FIRST LAST (DERBY NAME)"
        )

    def test_derby_name(self):
        # Derby name can be empty
        self.assertEqual(self.user.derby_name, '')

        # Can set a derby name
        self.user.derby_name = 'DERBY NAME'
        self.user.save()
        self.assertEqual(self.user.derby_name, 'DERBY NAME')

    def test_derby_number(self):
        # Derby number can be empty
        self.assertEqual(self.user.derby_number, '')

        # Can set a derby number
        self.user.derby_number = 'ABCD'
        self.user.save()
        self.assertEqual(self.user.derby_number, 'ABCD')

        # Maximum length of derby number is 4
        self.user.derby_number = 'ABCDE'
        with transaction.atomic():
            self.assertRaises(DataError, self.user.save)
              


    def test_is_not_staff(self):
        self.assertFalse(self.user.is_staff)


    def test_get_absolute_url(self):
        self.assertEqual(
            self.user.get_absolute_url(),
            '/users/{}/'.format(self.user.id)
        )
