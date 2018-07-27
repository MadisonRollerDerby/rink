from test_plus.test import TestCase
from guardian.shortcuts import get_perms_for_model

from users.models import User

from .factories import (
    UserFactory, LeagueAdminUserFactory, OrgAdminUserFactory, 
    user_password, league_member_permission,
    org_admin_permission, league_admin_permission,
)


class TestOrgAdminUser(TestCase):
    user_factory = OrgAdminUserFactory

    def setUp(self):
        self.user = self.make_user()


class TestUser(TestCase):
    user_factory = UserFactory

    def setUp(self):
        self.user = self.user_factory()

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

    def test_user_attributes(self):
        self.assertFalse(self.user.is_admin)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_staff)

    def test_user_login_session_with_league_organization(self):
        # Check session data from login signal
        # This user has a league and organzation set, so they will actually
        # have some data and permissions to check here.
        login_successful = self.client.login(
            email=self.user.email,
            password=user_password,
        )
        self.assertTrue(login_successful)
        session = self.client.session
        self.assertEqual(session["view_organization"], self.user.organization.pk)
        self.assertEqual(session["view_organization_slug"], self.user.organization.slug)
        self.assertEqual(session["organization_permissions"], [])
        self.assertEqual(session["view_league"], self.user.league.pk)
        self.assertEqual(session["view_league_slug"], self.user.league.slug)     
        self.assertEqual(session["league_permissions"], [league_member_permission])
        self.assertFalse(session["organization_admin"])
        self.assertFalse(session["league_admin"])



class TestRinkUserManager(TestCase):
    # Test the RinkUserManager methods to create a user and superuser.

    def test_create_user(self):
        # Try creating a user with an invalid email address
        with self.assertRaises(ValueError):
            user_invalid = User.objects.create_user(
                email="invalid",
            )

        # Create a user with no password
        user_no_password = User.objects.create_user(
            email="test-create-user@rink.com",
        )

        self.assertFalse(user_no_password.has_usable_password())

        # Create a user with normalized email address
        user = User.objects.create_user(
            email="TEST@RINK.COM",
            password=user_password,
        )
        # "Normalizes email addresses by lowercasing the domain 
        # portion of the email address."
        self.assertEqual(user.email, "TEST@rink.com")

        # User can log in
        login_successful = self.client.login(
            email=user.email,
            password=user_password,
        )
        self.assertTrue(login_successful)

        # User can login in with an all-caps or all-lowercase version also
        login_successful = self.client.login(
            email="TEST@RINK.COM",
            password=user_password,
        )
        self.assertTrue(login_successful)

        login_successful = self.client.login(
            email="test@rink.com",
            password=user_password,
        )
        self.assertTrue(login_successful)


        # Check attributes
        self.assertFalse(user.is_admin)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

        # Check session data from login signal
        # This user does not have a league or organization set, so these
        # should all be pretty much empty or false
        session = self.client.session
        self.assertIsNone(session["view_organization"])
        self.assertEqual(session["view_organization_slug"], '')
        self.assertEqual(session["organization_permissions"], [])
        self.assertIsNone(session["view_league"])
        self.assertEqual(session["view_league_slug"], None) # hmmm?        
        self.assertEqual(session["league_permissions"], [])
        self.assertFalse(session["organization_admin"])
        self.assertFalse(session["league_admin"])

    def test_create_org_admin(self):
        user = User.objects.create_superuser(
            email="test@rink.com",
            password=user_password,
        )

        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)


class TestLeagueAdminUser(TestCase):
    user_factory = LeagueAdminUserFactory

    def setUp(self):
        self.user = self.user_factory()

    def test_league_admin_login_session(self):
        login_successful = self.client.login(
            email=self.user.email,
            password=user_password,
        )
        self.assertTrue(login_successful)
        session = self.client.session
        self.assertEqual(session["view_organization"], self.user.organization.pk)
        self.assertEqual(session["view_organization_slug"], self.user.organization.slug)
        self.assertEqual(session["organization_permissions"], [])
        self.assertEqual(session["view_league"], self.user.league.pk)
        self.assertEqual(session["view_league_slug"], self.user.league.slug)   
        for perm in get_perms_for_model(self.user.league):  
            self.assertIn(perm.codename, session["league_permissions"])
        self.assertFalse(session["organization_admin"])
        self.assertTrue(session["league_admin"])


class TestOrgAdminUser(TestCase):
    user_factory = OrgAdminUserFactory

    def setUp(self):
        self.user = self.user_factory()

    def test_org_admin_login_session(self):
        login_successful = self.client.login(
            email=self.user.email,
            password=user_password,
        )
        self.assertTrue(login_successful)
        session = self.client.session
        self.assertEqual(session["view_organization"], self.user.organization.pk)
        self.assertEqual(session["view_organization_slug"], self.user.organization.slug)
        self.assertEqual(session["organization_permissions"], [org_admin_permission])
        self.assertEqual(session["view_league"], self.user.league.pk)
        self.assertEqual(session["view_league_slug"], self.user.league.slug)   
        for perm in get_perms_for_model(self.user.league):  
            self.assertIn(perm.codename, session["league_permissions"])
        self.assertTrue(session["organization_admin"])
        self.assertTrue(session["league_admin"])



