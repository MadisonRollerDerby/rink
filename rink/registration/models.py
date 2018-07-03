from django.db import models

from localflavor.us.forms import USZipCodeField
from localflavor.us.us_states import STATE_CHOICES
from phonenumber_field.modelfields import PhoneNumberField

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

    registration_open_datetime = models.DateTimeField(
        "Registration Opens At",
        blank = True,
        help_text = "The date/time that the registration form becomes available. If you set it to blank, registration is open now."
    )

    registration_closes_datetime = models.DateTimeField(
        "Registration Closes At",
        blank = True,
        help_text = "The date/time that the registration form becomes available. If you set it to blank, registration will never close."
    )

    def __str__(self):
        return "{}".format(self.name)


class RegistrationInvite(models.Model):
    user = models.ForeignKey(
        "users.User",
        blank=True,
        on_delete=models.CASCADE,
    )

    email = models.EmailField(
    )

    send_datetime = models.DateTimeField(
    )

    expiry = models.DateTimeField(
    )

    completed = models.DateTimeField(
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










