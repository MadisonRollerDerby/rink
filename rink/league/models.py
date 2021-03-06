from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify

from fernet_fields import EncryptedCharField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit
from localflavor.us.us_states import STATE_CHOICES

DAY_OF_MONTH_CHOICES = [(i,i) for i in range(1, 31)]
INVOICE_DAY_CHOICES = [(i, '{} days before due date'.format(i)) for i in range(1, 21)]
LATE_DAY_CHOICES = [(i, '{} days after due date'.format(i)) for i in range(1, 21)]


class InsuranceType(models.Model):
    name = models.CharField(
        "Insurer Name",
        max_length=50,
        help_text="Example: 'WFTDA'",
    )

    long_name = models.CharField(
        "Insurer Long Name",
        max_length=50,
        help_text="Example: 'Women's Flat Track Derby Association'",
        null=True,
        blank=True,
    )

    details_url = models.CharField(
        "Insurer Details URL",
        max_length=200,
        help_text="Link to sign up for insurance or get more information.",
        null=True,
        blank=True,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        unique_together = ['league', 'name']

    def get_absolute_url(self):
        return reverse('league:insurance_list', kwargs={
            'organization_slug': self.league.organization.slug,
            'slug': self.league.slug,
        })


class Organization(models.Model):
    
    """
    Top level organization, can contain multiple leagues.
    """


    name = models.CharField(
        "Organization Name",
        max_length=50,
        help_text = "Example: 'Madison Roller Derby', etc.",
    )

    slug = models.CharField(
        "Organization Slug",
        max_length=50,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
        unique=True,
        blank=True,
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

    short_name = models.CharField(
        "Short Name",
        max_length=50,
        help_text = "Example: 'MWD', 'Juniors', 'MRD', etc. Something short.",
    )

    slug = models.CharField(
        "League Slug",
        max_length=20,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
        blank=True,
    )

    organization = models.ForeignKey(
        'league.Organization',
        on_delete = models.CASCADE,
    )

    logo = models.ImageField(upload_to='logos', blank=True, null=True)
    logo_thumbnail = ImageSpecField(
        source='logo',
        processors=[ResizeToFill(100, 100)],
        format='JPEG',
        options={'quality': 80}
    )
    logo_thumbnail_header = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(50, 50)],
        format='PNG',
    )
    logo_thumbnail_footer = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(300, 300)],
        format='PNG',
    )
    logo_social = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(1200, 630)],
        format='PNG',
    )


    # Payment Settings

    default_payment_due_day = models.IntegerField(
        "Default Payment Due Day",
        choices=DAY_OF_MONTH_CHOICES,
        help_text="Default day of month to set billing due date.",
        default=1
    )

    default_invoice_day_diff = models.IntegerField(
        "Default Invoice Generation Day",
        choices=INVOICE_DAY_CHOICES,
        help_text="Default day to generate and email invoices.",
        default=10,
    )

    stripe_private_key = EncryptedCharField(
        "Stripe Secret Key",
        max_length=100,
        blank=True,
        help_text="Private/secret API key for Stripe.com. Used for charging credit cards.",
    )

    stripe_public_key = EncryptedCharField(
        "Stripe Public Key",
        max_length=100,
        blank=True,
        help_text="Private API key for Stripe.com. Used for charging credit cards.",
    )


    #  Registration Settings
    default_address_state = models.CharField(
        max_length=2,
        blank=True,
        choices=STATE_CHOICES,
        help_text="Default state choice on Registration forms.",
    )

    default_insurance_type = models.ForeignKey(
        'league.InsuranceType',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="Default insurance type to show on Registration forms.",
        related_name="default_insurance_type",
    )


    # Email Settings

    email_from_name = models.CharField(
        "Email From Name",
        max_length=100,
        help_text="The name of the person or account sending email. Example 'MRD Training'.",
        blank=True,
    )

    email_from_address = models.EmailField(
        "Email From Address",
        max_length=100,
        help_text="The email address all emails from this league will be from."
    )

    email_cc_address = models.EmailField(
        "CC Emails To",
        max_length=100,
        help_text="If you would like all emails sent from this league to be CC'd to an email, enter one here. Leave blank to disable.",
        blank=True,
    )

    email_signature = models.TextField(
        "Email Signature",
        help_text="Custom signature in HTML for all emails sent from this system.",
        blank=True,
    )

    style_color_one = models.CharField(
        "Style Color #1",
        max_length=20,
        help_text="First color for custom theme for this league. Default is '#F9FC69'.",
        blank=True,
    )

    style_color_two = models.CharField(
        "Style Color #2",
        max_length=20,
        help_text="Second color for custom theme for this league. Default is '#35E5F4'.",
        blank=True,
    )

    style_email_font = models.CharField(
        "Email Font CSS Name",
        max_length=100,
        help_text="The font to use for branding the logo in emails. Default is 'Lucida Sans Unicode', 'Lucida Grande', sans-serif'",
        blank=True,
    )

    style_header_font_name = models.CharField(
        "Header Font Google Font Name",
        max_length=100,
        help_text="The name of the font to use when loading the google font to use for the league name in the header. Default is 'Lobster'.",
        blank=True,
    )

    style_header_font_css = models.CharField(
        "Header Font Google Font CSS Font-Family",
        max_length=100,
        help_text="The font-face CSS to use for branding the league name in the header. Default is 'Lobster, cursive'.",
        blank=True,
    )



    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        unique_together = ('slug', 'organization')
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

    def get_stripe_private_key(self):
        if self.stripe_private_key:
            return self.stripe_private_key
        raise ImproperlyConfigured("Stripe private key not set for {}".format(self.name))

    def get_stripe_public_key(self):
        if self.stripe_public_key:
            return self.stripe_public_key
        raise ImproperlyConfigured("Stripe public key not set for {}".format(self.name))


@receiver(pre_save, sender=Organization)
@receiver(pre_save, sender=League)
def my_callback(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)
        