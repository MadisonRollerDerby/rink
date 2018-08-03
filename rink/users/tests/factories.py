import factory
from guardian.shortcuts import assign_perm

from league.tests.factories import OrganizationFactory, LeagueFactory

user_password = "test1ngISmag1c4l!"
league_member_permission = 'league_member'
league_admin_permission = 'league_admin'
org_admin_permission = 'org_admin'


class RinkUserFactory(factory.django.DjangoModelFactory):
    """
    Current permissions set looks like:

    - org_admin
    - league_admin
    - roster_manager
    - dues_manager
    - registration_manager
    - league_member
    """
    password = factory.PostGenerationMethodCall('set_password', user_password)

    league = factory.SubFactory(
        LeagueFactory,
        organization=factory.SelfAttribute('..organization')
    )
    organization = factory.SubFactory(OrganizationFactory)

    class Meta:
        model = 'users.User'
        django_get_or_create = ('email', )


class UserFactoryNoPermissions(RinkUserFactory):
    email = factory.Sequence(lambda n: f'noperms-{n}@madisonrollerderby.org')


class UserFactory(RinkUserFactory):
    email = factory.Sequence(lambda n: f'user-{n}@madisonrollerderby.org')

    @factory.post_generation
    def set_permissions(self, created, expected, **kwargs):
        assign_perm(league_member_permission, self, self.league)


class LeagueAdminUserFactory(RinkUserFactory):
    email = factory.Sequence(lambda n: f'leagueadmin-{n}@madisonrollerderby.org')

    @factory.post_generation
    def set_permissions(self, created, expected, **kwargs):
        assign_perm(league_admin_permission, self, self.league)


class OrgAdminUserFactory(RinkUserFactory):
    email = factory.Sequence(lambda n: f'orgadmin-{n}@madisonrollerderby.org')

    @factory.post_generation
    def set_permissions(self, created, expected, **kwargs):
        assign_perm(org_admin_permission, self, self.organization)

