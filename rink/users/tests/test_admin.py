from test_plus.test import TestCase

from .factories import UserFactory
from ..admin import MyUserCreationForm


class TestMyUserCreationForm(TestCase):

    user_factory = UserFactory

    def setUp(self):
        self.user = self.make_user('dev-test@madisonrollerderby.org', 'notalamodespassword')

    def test_clean_email_success(self):
        # Instantiate the form with a new email
        form = MyUserCreationForm({
            'email': 'dev-test2@madisonrollerderby.org',
            'password1': '7jefB#f@Cc7YJB]2v',
            'password2': '7jefB#f@Cc7YJB]2v',
        })
        # Run is_valid() to trigger the validation
        valid = form.is_valid()
        self.assertTrue(valid)

        # Run the actual clean_email method
        email = form.clean_email()
        self.assertEqual('dev-test2@madisonrollerderby.org', email)

    def test_clean_email_false(self):
        # Instantiate the form with the same email as self.user
        form = MyUserCreationForm({
            'email': self.user.email,
            'password1': 'notalamodespassword',
            'password2': 'notalamodespassword',
        })
        # Run is_valid() to trigger the validation, which is going to fail
        # because the email is already taken
        valid = form.is_valid()
        self.assertFalse(valid)

        # The form.errors dict should contain a single error called 'email'
        self.assertTrue(len(form.errors) == 1)
        self.assertTrue('email' in form.errors)
