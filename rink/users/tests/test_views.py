from django.core import mail
from django.test import RequestFactory
from django.urls import reverse

from django.test import TransactionTestCase
import pytest

from .factories import UserFactory, user_password

from ..views import UserProfileView

from league.models import League


@pytest.mark.usefixtures("celery_worker")
class TestUserProfileView(TransactionTestCase):
    def setUp(self):
        super(TestUserProfileView, self).setUp()
        self.user = UserFactory()
        self.factory = RequestFactory()
        self.view = UserProfileView()
        self.url = reverse('users:profile')

    def test_login_required(self):
        response = self.client.get(self.url)
        # Should redirect to /account/login?next=/users/profile or similar
        self.assertRedirects(
            response,
            '{}?next={}'.format(
                reverse('account_login'),
                self.url,
            )
        )

    def test_form_view(self):
        self.client.login(username=self.user.email, password=user_password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/rink_profile_update.html')

        # Test incomplete form
        response = self.client.post(self.url, {'email': 'invalid'}, follow=True)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')

        # Ensure the organization this user belongs to gets updated to have a
        # contact email for notifications
        league = League.objects.get(pk=self.user.league.pk)
        league.email_from_address = 'alert-test@rink.com'
        league.save()

        # Test complete form
        post_data = {
            'email': 'valid-email-changed@rink.com',
            'first_name': "changed first",
            'last_name': "changed last",
            'derby_name': "new derby name",
            'derby_number': "ABC999",
        }
        response = self.client.post(self.url, post_data, follow=True)

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, post_data['email'])
        self.assertEqual(self.user.first_name, post_data['first_name'])
        self.assertEqual(self.user.last_name, post_data['last_name'])
        self.assertEqual(self.user.derby_name, post_data['derby_name'])
        self.assertEqual(self.user.derby_number, post_data['derby_number'])

        # When the email is changed, we should have notified an admin
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('has updated their user details at', mail.outbox[0].subject)
