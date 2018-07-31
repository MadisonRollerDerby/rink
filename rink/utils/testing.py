from django.conf import settings
from django.urls import reverse, resolve
from guardian.shortcuts import get_perms_for_model, assign_perm, remove_perm

from league.tests.factories import LeagueFactory
from users.tests.factories import UserFactoryNoPermissions, user_password


class URLTestCase(object):
    def check_url(self, name, path, reverse_args=[], reverse_kwargs={}):
        self.assertEqual(reverse(name, args=reverse_args, kwargs=reverse_kwargs), path)
        self.assertEqual(resolve(path).view_name, name)


class RinkViewTest(object):
    org_perms_required = ['org_admin']
    league_perms_required = []  # by default we only assume org admins access it
    url = None
    url_kwargs = {}

    def setUp(self):
        super(RinkViewTest, self).setUp()
        self.league = LeagueFactory()
        self.organization = self.league.organization

    def _get_url(self):
        if not self.url:
            raise self.fail("URL not set for this test")
        self.reverse_url = reverse(self.url, kwargs=self.url_kwargs)
        return self.reverse_url

    def test_login_required(self):
        # Always assume login is required on these admin views
        response = self.client.get(self._get_url())
        # Should redirect to /account/login?next=/users/profile or similar
        # or permission denied, possibly.
        if response.status_code == 403:
            return

        self.assertRedirects(
            response,
            '{}?next={}'.format(
                reverse('account_login'),
                self.url,
            )
        )

    def test_league_permissions_required(self):
        # Check that the league manager position has the required permissions.

        perms_list = []
        # All league permissions, filtered by the ones we with to ignore.
        for perm in [perm for perm in get_perms_for_model(self.league)
                     if perm.codename not in settings.RINK_PERMISSIONS_IGNORE_TESTING]:
            perms_list.append((perm.codename, self.league))
        # All organization perms, filtered by the ones we wish to ignore.
        for perm in [perm for perm in get_perms_for_model(self.organization)
                     if perm.codename not in settings.RINK_PERMISSIONS_IGNORE_TESTING]:
            perms_list.append((perm.codename, self.organization))

        user = UserFactoryNoPermissions(organization=self.organization, league=self.league)
        for codename, obj in perms_list:
            assign_perm(codename, user, obj)

            self.client.login(email=user.email, password=user_password)
            response = self.client.get(self._get_url())

            self.assertIn(response.status_code, [200, 403], "URL {} returned code {} for {}".format(
                self.reverse_url, response.status_code, codename))

            if codename in self.org_perms_required or codename in self.league_perms_required:
                # Allowed access. Should respond with 200 and the correct template and view.
                self.assertEqual(response.status_code, 200,
                                "{} should have access to view and does not: ({}) T:{}".format(
                                    codename, self.reverse_url, self.template))
                self.assertTemplateUsed(response, self.template,
                                        "Wrong template being displayed by URL ({}) for user with permissions of {}".format(
                                            self.reverse_url, codename))
            else:
                # Disallowed access. 403. Should get access denied and use the 403.html template.
                self.assertEqual(response.status_code, 403,
                                "{} should not have access to URL: ({}) T:{}".format(
                                    codename, self.reverse_url, self.template))

                self.assertTemplateUsed(response, "403.html")
            self.client.logout()

            remove_perm(codename, user, obj)
