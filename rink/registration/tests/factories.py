from datetime import date, timedelta
import factory
from factory.fuzzy import FuzzyDate

from league.tests.factories import LeagueFactory


class RegistrationEventFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Registration Event {n}')
    league = factory.SubFactory(LeagueFactory)
    start_date = FuzzyDate(date(2000, 1, 1))
    end_date = FuzzyDate(date(2000, 12, 31))

    class Meta:
        model = 'registration.RegistrationEvent'


class RegistrationInviteFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'registration-invite-{n}@test.com')
    event = factory.SubFactory(RegistrationEventFactory)

    class Meta:
        model = 'registration.RegistrationInvite'
