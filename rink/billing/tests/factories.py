from datetime import timedelta, date
import factory
from factory.fuzzy import FuzzyInteger, FuzzyDate
import random

from league.tests.factories import LeagueFactory
from registration.tests.factories import RegistrationEventFactory
from users.tests.factories import UserFactory


class BillingGroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Billing Group {n}')
    league = factory.SubFactory(LeagueFactory)
    invoice_amount = FuzzyInteger(0, 100)

    class Meta:
        model = 'billing.BillingGroup'


class BillingPeriodFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Billing Period {n}')
    event = factory.SubFactory(RegistrationEventFactory)
    league = factory.SubFactory(LeagueFactory)
    start_date = FuzzyDate(date(2000, 1, 1))
    end_date = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=random.randrange(30, 365, 30)))
    invoice_date = factory.LazyAttribute(lambda o: o.start_date - timedelta(days=random.randint(7, 30)))
    due_date = factory.SelfAttribute('start_date')

    class Meta:
        model = 'billing.BillingPeriod'


class Invoice(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    billing_period = factory.SubFactory(BillingPeriodFactory,
        league=factory.LazyAttribute(lambda o: o.factory_parent.user.league),
    ),
    league = factory.SelfAttribute('user.league')
    description = factory.LazyAttribute(lambda o: "{} {}".format(
        o.billing_period.name, " Dues"))
    invoice_amount = FuzzyInteger(0, 100)
    invoice_date = factory.SelfAttribute('billing_period.invoice_date')
    due_date = factory.SelfAttribute('billing_period.due_date')

    class Meta:
        model = 'billing.Invoice'


class Payment(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    league = factory.SelfAttribute('user.league')
    processor = "stripe"
    amount = FuzzyInteger(0, 100)
    fee = FuzzyInteger(0, 4)


class UserStripeCard(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    league = factory.SelfAttribute('user.league')
