import factory
from factory.fuzzy import FuzzyInteger

from league.tests.factories import LeagueFactory


class BillingGroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Billing Group {n}')
    league = factory.SubFactory(LeagueFactory)
    invoice_amount = FuzzyInteger(0, 100)

    class Meta:
        model = 'billing.BillingGroup'
