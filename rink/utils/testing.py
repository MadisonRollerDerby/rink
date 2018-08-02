from django.conf import settings
from django.urls import reverse, resolve
from guardian.shortcuts import get_perms_for_model, assign_perm, remove_perm

from league.tests.factories import LeagueFactory
from users.tests.factories import UserFactory, UserFactoryNoPermissions, user_password


class URLTestCase(object):
    def check_url(self, name, path, reverse_args=[], reverse_kwargs={}):
        self.assertEqual(reverse(name, args=reverse_args, kwargs=reverse_kwargs), path)
        self.assertEqual(resolve(path).view_name, name)


class RinkViewTest(object):
    organization_permissions_required = ['org_admin']
    league_permissions_required = []  # by default we only assume org admins access it

    is_public = False  # Access to this view is not restricted
    skip_permissions_tests = False  # Skip permission checks in the test
    template = None  # Template file that should be expected by assertTemplateUsed
    redirect = None  # If this view redirects, this is our final destination
    url = None  # URL name to request a page from, with namespace

    _url_kwargs = {}

    def setUp(self):
        super(RinkViewTest, self).setUp()
        try:
            self.league
            self.organization
        except AttributeError:
            self.league = LeagueFactory()
            self.organization = self.league.organization

    def tearDown(self):
        super(RinkViewTest, self).tearDown()

    def reset(self):
        self.tearDown()
        self.setUp()

    def user_factory(self, *args, **kwargs):
        return UserFactory(organization=self.organization, league=self.league, **kwargs)

    # Additional kwargs to use for reverse lookup below.
    def url_kwargs(self):
        super(RinkViewTest, self).url_kwargs()
        return {}

    def get_url(self):
        if not self.url:
            raise self.fail("URL not set for this test")

        # Custom kwargs can be returned by url_kwargs method
        try:
            self._url_kwargs = {**self._url_kwargs, **self.url_kwargs()}
        except AttributeError:
            pass

        self.reverse_url = reverse(self.url, kwargs=self._url_kwargs)
        return self.reverse_url

    def test_login_required(self):
        # This test is not required for this view, it is publically accessible.
        if self.is_public:
            return

        # Always assume login is required on these admin views
        response = self.client.get(self.get_url())
        # Should redirect to /account/login?next=/users/profile or similar
        # or permission denied, possibly.
        if response.status_code == 403:
            return

        self.assertRedirects(
            response,
            '{}?next={}'.format(reverse('account_login'), self.reverse_url))

    def test_league_permissions_and_template(self):
        # A combinations of attributes automatically tests some or all of the following:
        # Test for permissions and access
        # Test for correct templates or redirects
        # Test that a user can access the page

        # View should be publically accessable
        if self.is_public:
            # Simply check the template returned for now.
            response = self.client.get(self.get_url())
            if self.template:
                self.assertTemplateUsed(response, self.template)
            if self.redirect:
                self.assertRedirects(response, self.redirect)
            if not self.template and not self.redirect:
                self.fail("Did not check either a template or redirect for this test.")
            return

        user = UserFactoryNoPermissions(organization=self.organization, league=self.league)

        if self.skip_permissions_tests:
            self.client.login(email=user.email, password=user_password)
            response = self.client.get(self.get_url())
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template,
                "Wrong template being displayed by URL ({})".format(self.reverse_url))

        else:
            perms_list = []
            # All league permissions, filtered by the ones we with to ignore.
            for perm in [perm for perm in get_perms_for_model(self.league)
                         if perm.codename not in settings.RINK_PERMISSIONS_IGNORE_TESTING]:
                perms_list.append((perm.codename, self.league))
            # All organization perms, filtered by the ones we wish to ignore.
            for perm in [perm for perm in get_perms_for_model(self.organization)
                         if perm.codename not in settings.RINK_PERMISSIONS_IGNORE_TESTING]:
                perms_list.append((perm.codename, self.organization))

            for codename, obj in perms_list:
                assign_perm(codename, user, obj)
                # Assign the permission before we login to ensure session data is set.
                self.client.login(email=user.email, password=user_password)
                response = self.client.get(self.get_url())

                self.assertIn(response.status_code, [200, 403], "URL {} returned code {} for {}".format(
                    self.reverse_url, response.status_code, codename))

                if codename in self.organization_permissions_required or codename in self.league_permissions_required:
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
