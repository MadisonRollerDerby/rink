from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify

from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


class LegalDocument(models.Model):
    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        "Document Name",
        max_length=100,
        help_text = "Name of this legal document.",
    )

    slug = models.CharField(
        "Slug",
        max_length=100,
        blank=True,
    )

    date = models.DateField(
        "Effective Date",
        help_text="Effective date of this legal document.",
    )

    content = models.TextField(
        "Document Content",
        help_text="Plaintext version of the legal document. You can use <a target='_blank' href='https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet'>Markdown Code</a> to format the document.",
    )

    def __str__(self):
        return "{} ({})".format(self.name, self.date)

    @property
    def content_html(self):
        return markdownify(self.content)

    def get_absolute_url(self):
        return reverse('legal:view_legal_document', 
            kwargs={'league_slug': self.league.slug, 'document_slug': self.slug })

    class Meta:
        unique_together = ('slug', 'league')
        ordering = ['date', 'name']


class LegalSignature(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    document = models.ForeignKey(
        'legal.LegalDocument',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    event = models.ForeignKey(
        'registration.RegistrationEvent',
        on_delete=models.SET_NULL,
        null=True,
    )

    registration = models.ForeignKey(
        'registration.RegistrationData',
        on_delete=models.SET_NULL,
        null=True,
    )

    agree_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} - {} - {}".format(self.user, self.document, self.league)

    class Meta:
        ordering = ['agree_date', 'document__name']


@receiver(pre_save, sender=LegalDocument)
def slugify_legal_document(sender, instance, *args, **kwargs):
    instance.slug = slugify("{} {}".format(instance.name, instance.date))

    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass # new object
    else:
        has_signatures = LegalSignature.objects.filter(document=obj)
        if has_signatures and (not obj.content == instance.content or not obj.date == instance.date):
            raise ValidationError("You cannot change the content or date of this legal document, as {} have signed it. Create a new legal document.".format(has_signatures.count()))
