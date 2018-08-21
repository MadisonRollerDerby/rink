from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify
import uuid

from dateutil import rrule
from dateutil.relativedelta import relativedelta
from localflavor.us.forms import USZipCodeField
from localflavor.us.us_states import STATE_CHOICES
from markdownx.utils import markdownify

from billing.models import BillingPeriod, BillingGroup
from league.models import Organization, League
from users.models import User


class RegistrationEvent(models.Model):
    name = models.CharField(
        "Event Name",
        max_length=50,
        help_text="Example: 'Summer Skating', 'MRD 2018 Registration'",
    )

    slug = models.SlugField(
        "Event Slug",
        max_length=50,
        help_text="Example: 'summer-skating-2018', is used for the registration URL.",
        blank=True,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    description = models.TextField(
        "Event Description",
        blank=True,
        help_text="Blurb of text shown at the <strong>top of the registration form</strong> and <strong>included in the registration confirmation email.</strong> You can use <a target='_blank' href='https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet'>Markdown Code</a> to format the document."
    )

    legal_blurb = models.TextField(
        "Legal Blurb",
        blank=True,
        help_text="Blurb of text shown in the <strong>legal section</strong> and <strong>included in the registration confirmation email.</strong> You can use <a target='_blank' href='https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet'>Markdown Code</a> to format the document."
    )

    payment_blurb = models.TextField(
        "Payment Blurb",
        blank=True,
        help_text="Blurb of text shown in the <strong>payment section</strong> and <strong>included in the registration confirmation email.</strong> You can use <a target='_blank' href='https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet'>Markdown Code</a> to format the document."
    )

    @property
    def description_html(self):
        return markdownify(self.description)

    @property
    def legal_blurb_html(self):
        return markdownify(self.legal_blurb)

    @property
    def payment_blurb_html(self):
        return markdownify(self.payment_blurb)

    start_date = models.DateField(
        "Start Date",
        help_text="First day of this session.",
    )

    end_date = models.DateField(
        "End Date",
        help_text="Last day of this session.",
    )

    public_registration_open_date = models.DateTimeField(
        "Registration Opens On",
        blank=True,
        null=True,
        help_text="The date/time that the registration form becomes available. If you set it to blank, registration is open now.",
    )

    public_registration_closes_date = models.DateTimeField(
        "Registration Closes On",
        blank=True,
        null=True,
        help_text="The date/time that the registration form becomes available. If you set it to blank, registration will never close.",
    )

    invite_expiration_date = models.DateTimeField(
        "Invites Expire On",
        blank=True,
        null=True,
        help_text="People who are invited must register before this date. Invites will no longer work after this date. If you set this to blank, invites will always work.",
    )

    minimum_registration_age = models.IntegerField(
        "Minimum Age (Years)",
        blank=True,
        null=True,
        help_text="The minimum age someone can register for this event. Calculated based on the Start Date. Leave blank to disable this check.",
    )

    maximum_registration_age = models.IntegerField(
        "Maximum Age (Years)",
        blank=True,
        null=True,
        help_text="The maximum age someone can register for this event. Calculated based on the Start Date. Leave blank to disable this check.",
    )

    legal_forms = models.ManyToManyField(
        'legal.LegalDocument',
    )

    class Meta:
        unique_together = ('slug', 'league')

    def __str__(self):
        return "{}".format(self.name)

    def create_billing_period(self, name=None, start_date=None, end_date=None):
        if not name:
            name = "{} - Registration Dues".format(self.name)
        if not start_date:
            start_date = self.start_date
        if not end_date:
            end_date = self.end_date

        invoice_date = start_date - relativedelta(days=self.league.default_invoice_day_diff)
        due_date = start_date

        return BillingPeriod.objects.create(
            name=name,
            league=self.league,
            event=self,
            start_date=start_date,
            end_date=end_date,
            invoice_date=invoice_date,
            due_date=due_date,
        )

    def create_monthly_billing_periods(self):
        periods = []
        for dt in rrule.rrule(rrule.MONTHLY, dtstart=self.start_date, until=self.end_date):
            month_start = dt
            month_end = dt + relativedelta(months=1) - relativedelta(days=1)
            period = self.create_billing_period(
                name="{} Dues".format(dt.strftime('%B')),
                start_date=month_start,
                end_date=month_end,
            )
            periods.append(period)

        return periods

    def get_kwargs_for_url(self):
        return {
            'organization_slug': self.league.organization.slug,
            'league_slug': self.league.slug,
            'event_slug': self.slug,
        }

    def get_legal_forms_url(self):
        return reverse('legal:view_event_legal_documents',
            kwargs={'league_slug': self.league.slug, 'event_slug': self.slug})

    def get_invites_url(self):
        return reverse('registration:event_admin_invites', kwargs=self.get_kwargs_for_url())

    def get_roster_url(self):
        return reverse('registration:event_admin_roster', kwargs=self.get_kwargs_for_url())

    def get_settings_url(self):
        return reverse('registration:event_admin_settings', kwargs=self.get_kwargs_for_url())

    def get_billing_periods_url(self):
        return reverse('registration:event_admin_billing_periods', kwargs=self.get_kwargs_for_url())

    # def get_absolute_url(self):


@receiver(pre_save, sender=RegistrationEvent)
def set_registration_event_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)


class RegistrationInvite(models.Model):
    user = models.ForeignKey(
        "users.User",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    email = models.EmailField(
        "Email Address",
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        on_delete=models.CASCADE,
    )

    billing_group = models.ForeignKey(
        "billing.BillingGroup",
        on_delete=models.SET_NULL,
        null=True,
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    sent_date = models.DateTimeField(
        "Date Sent",
        blank=True,
        null=True,
    )

    completed_date = models.DateTimeField(
        "Registration Completed",
        blank=True,
        null=True,
    )

    public_registration = models.BooleanField(
        "Public Registration",
        blank=True,
        default=False,
    )

    def __str__(self):
        return "{}".format(self.email)

    def get_invite_url(self):
        return reverse("register:register_event_uuid", kwargs={
            'league_slug': self.event.league.slug,
            'event_slug': self.event.slug,
            'invite_key': self.uuid,
        })


class RegistrationData(models.Model):

    invite = models.ForeignKey(
        "registration.RegistrationInvite",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    roster = models.ForeignKey(
        "registration.Roster",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    billing_subscription = models.ForeignKey(
        "billing.BillingSubscription",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    organization = models.ForeignKey(
        "league.Organization",
        on_delete=models.CASCADE,
    )

    contact_email = models.EmailField("Email Address")
    contact_first_name = models.CharField("First Name", max_length=100)
    contact_last_name = models.CharField("Last Name", max_length=100)
    contact_address1 = models.CharField("Address 1", max_length=100)
    contact_address2 = models.CharField("Address 2", max_length=100, blank=True)
    contact_city = models.CharField("City", max_length=100)
    contact_state = models.CharField("State", choices=STATE_CHOICES, max_length=2)
    contact_zipcode = models.CharField("Zip Code", max_length=11)
    contact_phone = models.CharField("Phone Number", max_length=25)

    derby_name = models.CharField(
        "Derby Name",
        max_length=100,
        help_text="Not required. Guidance document link is where?",
        blank=True
    )
    derby_number = models.CharField(
        "Derby Number",
        max_length=10,
        help_text="Not required. Guidance document link is where?",
        blank=True
    )
    
    derby_insurance_type = models.ForeignKey(
        'league.InsuranceType',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="If you have Derby insurance, specify it here. Insurance may not be required."
    )

    derby_insurance_number = models.CharField(
        "Derby Insurance Number",
        max_length=50,
        help_text="Derby insurance details. Insurance may not be required.",
        blank=True,
    )

    derby_pronoun = models.CharField(
        "Personal Pronoun",
        max_length=50,
        help_text="Optional. Examples: her/she, he/her, etc.",
        blank=True
    )

    emergency_date_of_birth = models.DateField(
        "Date of Birth",
    )
    emergency_contact = models.CharField(
        "Emergency Contact Name",
        max_length=100,
    )
    emergency_phone = models.CharField(
        "Emergency Phone Contact",
        max_length=25
    )
    emergency_relationship = models.CharField(
        "Emergency Contact Relationship", 
        max_length=100,
    )
    emergency_hospital = models.CharField(
        "Preferred Hospital Name",
        max_length=100,
    )
    emergency_allergies = models.TextField(
        "Allergies and Medical Conditions.\n\nPlease write 'none' if you have no medical concerns we might need to know about.",
        #help_text="If you have none, please write 'none'.",
    )

    legal_forms = models.ManyToManyField(
        'legal.LegalDocument',
    )

    registration_date = models.DateTimeField(
        "Registration Date",
        auto_now_add=True,
    )


class Roster(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    email = models.EmailField("Email Address")
    
    first_name = models.CharField("First Name", max_length=100)
    last_name = models.CharField("Last Name", max_length=100)

    derby_name = models.CharField(
        "Derby Name",
        max_length=100,
        blank=True
    )
    derby_number = models.CharField(
        "Derby Number",
        max_length=10,
        blank=True
    )

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)