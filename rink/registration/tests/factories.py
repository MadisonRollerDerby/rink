from datetime import date, timedelta
import factory
from factory.fuzzy import FuzzyDate
import random

from league.tests.factories import (
    LeagueFactory, OrganizationFactory, InsuranceTypeFactory)
from users.tests.factories import UserFactory

from rink.utils.testing import get_random_first_last_name, get_random_derby_name


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


class RegistrationDataFactoryMinimumFields(factory.django.DjangoModelFactory):
    invite = factory.SubFactory(RegistrationInviteFactory)
    user = factory.SubFactory(UserFactory)
    event = factory.SubFactory(RegistrationEventFactory)
    organization = factory.SubFactory(OrganizationFactory)

    contact_email = factory.SelfAttribute('user.email')
    contact_address1 = factory.Sequence(lambda n: f'{n} Test St')
    contact_address2 = factory.Sequence(lambda n: f'Apartment #{n}')
    contact_city = "Test City"
    contact_state = "WI"
    contact_zipcode = "12345-1234"
    contact_phone = "4444444444"

    emergency_date_of_birth = FuzzyDate(date(1945, 12, 31))
    emergency_contact = "Emergency Contact Test Person"
    emergency_phone = "1231231234"
    emergency_relationship = "Test Spouse"
    emergency_hospital = "Test Hospital"
    emergency_allergies = "nothing to note here thanks"

    class Meta:
        model = 'registration.RegistrationData'

    @factory.post_generation
    def set_first_last_name(self, created, expected, **kwargs):
        if self.user.first_name and self.user.last_name:
            self.contact_first_name = self.user.first_name
            self.contact_last_name = self.user.last_name
        else:
            self.contact_first_name, self.contact_last_name = get_random_first_last_name()


class RegistrationDataFactory(RegistrationDataFactoryMinimumFields):
    derby_insurance_type = factory.SubFactory(InsuranceTypeFactory)
    derby_insurance_number = factory.Sequence(lambda n: f'{n}')
    derby_pronoun = "test/tester"

    @factory.post_generation
    def set_derby_name_number_insurance(self, created, expected, **kwargs):
        if self.user.derby_name:
            self.derby_name = self.user.derby_name
        else:
            self.derby_name = get_random_derby_name()

        if self.user.derby_number:
            self.derby_number = self.user.derby_number
        else:
            self.derby_number = str(random.randint(0, 9999))
