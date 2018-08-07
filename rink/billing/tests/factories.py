from datetime import timedelta, date
from django.utils import timezone
import factory
from factory.fuzzy import FuzzyInteger, FuzzyDate
import random

from league.tests.factories import LeagueFactory
from registration.tests.factories import RegistrationEventFactory
from users.tests.factories import UserFactory


class BillingGroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Test Billing Group {n}')
    league = factory.SubFactory(LeagueFactory)
    invoice_amount = FuzzyInteger(10, 500)

    class Meta:
        model = 'billing.BillingGroup'


class BillingGroupMembershipFactory(factory.django.DjangoModelFactory):
    group = factory.SubFactory(BillingGroupFactory)
    league = factory.SubFactory(LeagueFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = 'billing.BillingGroupMembership'


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


class InvoiceFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    billing_period = factory.SubFactory(BillingPeriodFactory,
        league=factory.LazyAttribute(lambda o: o.factory_parent.user.league),
    ),
    league = factory.SelfAttribute('user.league')
    invoice_amount = FuzzyInteger(1, 100)
    invoice_date = timezone.now()
    due_date = timezone.now()

    class Meta:
        model = 'billing.Invoice'

    @factory.post_generation
    def set_description_and_dates(self, created, expected, **kwargs):
        self.description = "{} Dues".format(self.billing_period.name)
        self.invoice_date = self.billing_period.invoice_date
        self.due_date = self.billing_period.due_date


class PaymentFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    league = factory.SelfAttribute('user.league')
    processor = "stripe"
    amount = FuzzyInteger(0, 100)
    fee = FuzzyInteger(0, 4)

    class Meta:
        model = 'billing.Payment'


class PaymentFactoryWithCard(PaymentFactory):
    card_type = "visa"
    card_last4 = FuzzyInteger(1000, 9999)
    card_expire_month = 12
    card_expire_year = 2022
    payment_date = timezone.now()


class PaymentFactoryWithRefund(PaymentFactoryWithCard):
    refund_date = timezone.now()
    refund_amount = factory.SelfAttribute('amount')
    refund_reason = "nothing"


class UserStripeCardFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    league = factory.SelfAttribute('user.league')
    customer_id = "cus_123456789"
    card_type = "visa"
    card_last4 = FuzzyInteger(1000, 9999)
    card_expire_month = 11
    card_expire_year = 2024

    class Meta:
        model = 'billing.UserStripeCard'
