from django.db import models
from django.urls import reverse

from fernet_fields import EncryptedCharField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from localflavor.us.us_states import STATE_CHOICES


class Organization(models.Model):
    
    """
    Top level organization, can contain multiple leagues.
    """


    name = models.CharField(
        "Organization Name",
        max_length=50,
        help_text = "Example: 'Wreckers', 'Juniors', 'Madison Roller Derby', etc.",
    )

    slug = models.CharField(
        "Organization Slug",
        max_length=20,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        permissions = (
            ('org_admin', 'Can manage organization settings, create leagues and more.'),
        )


class League(models.Model):
    """
    A leauge will contain a group of users and logically separate registration and billing
    events.
    """

    name = models.CharField(
        "League Name",
        max_length=50,
        help_text = "Example: 'Wreckers', 'Juniors', 'Madison Roller Derby', etc.",
    )

    slug = models.CharField(
        "League Slug",
        max_length=20,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
    )

    organization = models.ForeignKey(
        'league.Organization',
        on_delete = models.CASCADE,
    )

    stripe_private_key = EncryptedCharField(
        "Stripe Private Key",
        max_length = 100,
        blank = True,
        help_text = "Private API key for Stripe.com. Used for charging credit cards.",
    )

    stripe_public_key = EncryptedCharField(
        "Stripe Public Key",
        max_length = 100,
        blank = True,
        help_text = "Private API key for Stripe.com. Used for charging credit cards.",
    )

    default_address_state = models.CharField(
        max_length=2,
        blank=True,
        choices=STATE_CHOICES,
        help_text = "Default state choice on Registration forms.",
    )

    logo = models.ImageField(upload_to='logos', blank=True, null=True)
    logo_thumbnail = ImageSpecField(
        source='logo',
        processors=[ResizeToFill(100, 100)],
        format='JPEG',
        options={'quality': 80}
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        permissions = (
            ('league_admin', 'Can manage league settings and email templates.'),
            ('billing_manager', 'Can send bills and manage dues.'),
            ('roster_manager', 'Can manage user profiles and assign people to teams.'),
            ('registration_manager', 'Can manage registration system and send invites.'),
            ('survey_manager', 'Can manage voting and surveys.'),
            ('event_manager', 'Can manage special event pages.'),
            ('league_member', 'Active member of league.'),
            
        )

    def get_absolute_url(self):
        return reverse('league:league_update', kwargs={'slug': self.slug, 'organization_slug': self.organization.slug })
        