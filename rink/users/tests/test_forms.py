from django.test import TestCase
from users.forms import UserProfileForm


class UserProfileFormTest(TestCase):
    def test_form(self):
        # Test with no data supplied
        # email is required
        form_data = {}
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid(), "Email not supplied but form validated")

        # Test with invalid email
        form_data = {
            'email': 'not an email address',
        }
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid(), "Email is invalid, but form validated")

        # Test with minimum required form data
        form_data = {
            'email': 'test@test.com',
        }
        form = UserProfileForm(data=form_data)
        self.assertTrue(form.is_valid(), "Form is not valid with only email address")

        # Test with all required form fields
        form_data = {
            'email': 'test@test.com',
            'first_name': "FIRST",
            'last_name': "LAST",
            'derby_name': "DERBY NAME",
            'derby_number': "DERBY NUMBER",
        }
        form = UserProfileForm(data=form_data)
        self.assertTrue(form.is_valid(), "Form is not valid but all fields were filled out.")
