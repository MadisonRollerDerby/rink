from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django.utils.text import slugify

from .factories import LegalDocumentFactory
from league.tests.factories import LeagueFactory
from legal.models import LegalDocument

import itertools


class TestLegalDocumentModel(TestCase):
    document_factory = LegalDocumentFactory

    def test_required_fields(self):
        # all fields are required, just try a blank object here.
        doc = LegalDocument()

        with self.assertRaises(ValidationError):
            doc.full_clean()
            doc.save()

    def test_can_create_document(self):
        # Check that we can actually create an object with sane attributes here
        document = LegalDocument(
            name="Test Document",
            league=LeagueFactory(),
            date="2000-10-10",
            content="Test Content!",
        )
        document.full_clean()
        document.save()

    def test_slug_post_save_signal(self):
        # Check that the slug is correctly populated by the pre-save signal.
        document = self.document_factory()

        self.assertEqual(
            document.slug, 
            slugify("{} {}".format(document.name, document.date))
        )

    def test_slug_resolve_duplicate_slugs_for_league(self):
        # Test that we are enforcing unique slugs on a per-league basis
        league = LeagueFactory()

        document1 = self.document_factory(name="Duplicate", league=league)
        document2 = self.document_factory(name="Duplicate", league=league)

        self.assertNotEqual(document1.slug, document2.slug)

    def test_slug_resolve_uduplicates_with_reasonable_amount_of_tries(self):
        league = LeagueFactory()

        # Check that the signal throws a validation error when we push the
        # limits of creating leagues. Let's try an unreasonable amount of times?
        unreasonable_amount_of_tries = 1000
        date = timezone.now().date()

        self.assertGreater(unreasonable_amount_of_tries, settings.SLUG_RESOLVE_DUPLICATES_LIMIT)

        for try_counter in itertools.count(1):
            doc = self.document_factory(name="Duplicate of Many", league=league, date=date)

            # If we're at the point where it should throw an error, expect it...
            if try_counter == settings.SLUG_RESOLVE_DUPLICATES_LIMIT:
                with self.assertRaises(ValidationError):
                    doc = self.document_factory(name="Duplicate of Many", league=league, date=date)
                break
            # Put it some kind of safety here, I guess?
            self.assertLess(try_counter, unreasonable_amount_of_tries)

    def test_slug_unique_per_league(self):
        # Slugs should be unique per league, which means multiple leagues
        # can share the same slug.
        league1 = LeagueFactory()
        league2 = LeagueFactory()

        document1 = self.document_factory(name="Duplicate", league=league1)
        document2 = self.document_factory(name="Duplicate", league=league2)

        self.assertEqual(document1.slug, document2.slug)
        self.assertNotEqual(
            document1.get_absolute_url(),
            document2.get_absolute_url()
        )
    
    def test_content_markdown_encode_html(self):
        # Test that the content_html property actually encodes a bit of
        # markdown formatted text into HTML.
        document = self.document_factory(content="**test**")
        self.assertEqual("<p><strong>test</strong></p>", document.content_html)

    def test_league_cascade_delete(self):
        # Test that we're properly removing the documents when a league is deleted.
        league = LeagueFactory()
        document = self.document_factory(league=league)

        doc_pk = document.pk

        league.delete()

        with self.assertRaises(LegalDocument.DoesNotExist):
            document = LegalDocument.objects.get(pk=doc_pk)

    # def test_disable_delete_if_signed


#class TestLegalSignatureModel(TestCase):
#    document_factory = LegalDocumentFactory

