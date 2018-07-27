import factory


class OrganizationFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Organization {n}')

    class Meta:
        model = 'league.Organization'


class LeagueFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test League {n}')
    organization = factory.SubFactory(OrganizationFactory)

    class Meta:
        model = 'league.League'
