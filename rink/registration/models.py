from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify

from dateutil import rrule
from dateutil.relativedelta import relativedelta
from localflavor.us.forms import USZipCodeField
from localflavor.us.us_states import STATE_CHOICES
from phonenumber_field.modelfields import PhoneNumberField

from billing.models import BillingPeriod
from league.models import Organization , League
from users.models import User


class RegistrationEvent(models.Model):
    name = models.CharField(
        "Event Name",
        max_length=50,
        help_text = "Example: 'Summer Skating', 'MRD 2018 Registration'",
    )

    slug = models.SlugField(
        "Event Slug",
        max_length=50,
        help_text = "Example: 'summer-skating-2018', is used for the registration URL.",
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    start_date = models.DateField(
        "Start Date",
        help_text = "First day of this session.",
    )

    end_date = models.DateField(
        "End Date",
        help_text = "Last day of this session.",
    )

    public_registration_open_date = models.DateTimeField(
        "Registration Opens On",
        blank = True,
        null = True,
        help_text = "The date/time that the registration form becomes available. If you set it to blank, registration is open now.",
    )

    public_registration_closes_date = models.DateTimeField(
        "Registration Closes On",
        blank = True,
        null = True,
        help_text = "The date/time that the registration form becomes available. If you set it to blank, registration will never close.",
    )

    invite_expiration_date = models.DateTimeField(
        "Invites Expire On",
        blank = True,
        null = True,
        help_text = "People who are invited must register before this date. Invites will no longer work after this date. If you set this to blank, invites will always work.",
    )

    minimum_registration_age = models.IntegerField(
        "Minimum Age (Years)",
        blank = True,
        null = True,
        help_text = "The minimum age someone can register for this event. Calculated based on the Start Date. Leave blank to disable this check.",
    )

    maximum_registration_age = models.IntegerField(
        "Maximum Age (Years)",
        blank = True,
        null = True,
        help_text = "The maximum age someone can register for this event. Calculated based on the Start Date. Leave blank to disable this check.",
    )

    class Meta:
        unique_together = ('slug', 'league')

    def __str__(self):
        return "{}".format(self.name)

    def create_billing_period(self, name=None, start_date=None, end_date=None):
        
        if not name:
            name = "{} - One Time Dues".format(self.name)
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

    def create_monthly_biling_periods(self):
        periods = []
        for dt in rrule.rrule(rrule.MONTHLY, dtstart=self.start_date, until=self.end_date):
            month_start = dt
            month_end = dt + relativedelta(months=1) - relativedelta(days=1)
            period = self.create_billing_period(
                name = "{} - {} Dues".format(self.name, dt.strftime('%B')),
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

    def get_invites_url(self):
        return reverse('registration:event_admin_invites', kwargs=self.get_kwargs_for_url())

    def get_roster_url(self):
        return reverse('registration:event_admin_roster', kwargs=self.get_kwargs_for_url())

    def get_settings_url(self):
        return reverse('registration:event_admin_settings', kwargs=self.get_kwargs_for_url())

    def get_billing_periods_url(self):
        return reverse('registration:event_admin_billing_periods', kwargs=self.get_kwargs_for_url())

    #def get_absolute_url(self):
        

@receiver(pre_save, sender=RegistrationEvent)
def my_callback(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)



 
class RegistrationInvite(models.Model):
    user = models.ForeignKey(
        "users.User",
        blank=True,
        on_delete=models.CASCADE,
    )

    email = models.EmailField(
        "Email Address",
    )

    event = models.ForeignKey(
        "registration.RegistrationEvent",
        on_delete=models.CASCADE,
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

    def __str__(self):
        return "{}".format(self.email)


class RegistrationData(models.Model):

    invite = models.ForeignKey(
        "registration.RegistrationInvite",
        blank=True,
        on_delete=models.CASCADE
    )
    
    contact_email = models.EmailField()
    contact_first_name = models.CharField("First Name", max_length=100)
    contact_last_name = models.CharField("Last Name", max_length=100)
    contact_address1 = models.CharField("Address 1", max_length=100)
    contact_address2 = models.CharField("Address 2", max_length=100)
    contact_city = models.CharField("City", max_length=100)
    state = models.CharField("State", choices=STATE_CHOICES, max_length=2)
    #contact_zipcode = USZipCodeField("Zip Code")
    contact_zipcode = models.CharField("Zip Code", max_length=11)
    contact_phone = PhoneNumberField("Phone Number")

    derby_name = models.CharField("Derby Name", max_length=100)
    derby_number = models.CharField("Derby Number", max_length=10)
    derby_pronoun = models.CharField("Personal Pronoun", max_length=50)
    derby_insurance_type = models.CharField("Derby Insurance", max_length=50)
    derby_insurance_number = models.CharField("Derby Insurance Number", max_length=50)

    emergency_date_of_birth = models.DateField("Date of Birth")
    emergency_contact = models.CharField("Derby Name", max_length=100)
    emergency_phone = PhoneNumberField("Emergency Phone Contact")
    emergency_relationship = models.CharField("Emergency Relationship", max_length=100)
    emergency_hospital = models.CharField("Preferred Hospital", max_length=100)
    emergency_allergies = models.TextField("Allergies and Medical Conditions")







