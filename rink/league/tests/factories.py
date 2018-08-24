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


class InsuranceTypeFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'TEST INSUR {n}')
    long_name = factory.Sequence(lambda n: f'Test Insurance Type {n}')
    details_url = "https://example.com"
    league = factory.SubFactory(LeagueFactory)

    class Meta:
        model = 'league.InsuranceType'
