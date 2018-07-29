from django.utils import timezone

import factory

from league.tests.factories import LeagueFactory
from users.tests.factories import UserFactory

class LegalDocumentFactory(factory.django.DjangoModelFactory):
    league = factory.SubFactory(LeagueFactory)
    name = factory.Sequence(lambda n: f'Legal Document Test {n}')
    date = timezone.now()
    content = factory.Sequence(lambda n: f'Here is some generic text for Document Test {n}')

    class Meta:
        model = "legal.LegalDocument"

"""
class LegalSignatureFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    document = factory.SubFactory(LegalDocumentFactory)
    league = factory.SubFactory(LeagueFactory)
    event = 
    registration = 

    class Meta:
        model = "legal.LegalDocumentSignature"
"""