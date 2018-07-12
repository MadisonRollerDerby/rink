from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field
from django import forms
from django.core.validators import RegexValidator
from django.forms import TextInput

from billing.models import BillingPeriod
from registration.models import RegistrationData, RegistrationEvent


AUTOMATIC_BILLING_CHOICES = (
    ('', 'None - Custom'),
    ('once', 'Bill Only Once'),
    ('monthly', 'Bill Monthly'),
)


class RegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = RegistrationData
        exclude = ['invite',]


class RegistrationAdminEventForm(forms.ModelForm):
    automatic_billing_dates = forms.ChoiceField(
        label="Create automatic billing dates?",
        choices=AUTOMATIC_BILLING_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super(RegistrationAdminEventForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            Fieldset(
                'Details',
                'name',
                'automatic_billing_dates',
                'start_date',
                'end_date',
            ),
            Fieldset(
                'Optional Dates',
                'public_registration_open_date',
                'public_registration_closes_date',
                'invite_expiration_date',
            ),
            Fieldset(
                'Settings',
                'minimum_registration_age',
                'maximum_registration_age',
            ),
            ButtonHolder(
                Submit('submit', 'Save Event', css_class='button white')
            )
        )


    class Meta:
        model = RegistrationEvent
        
        fields = [
            'name',
            'start_date',
            'end_date',
            'public_registration_open_date',
            'public_registration_closes_date',
            'invite_expiration_date',
            'minimum_registration_age',
            'maximum_registration_age',
        ]
        widgets = {
            'start_date': TextInput(attrs={'type':'date'}),
            'end_date': TextInput(attrs={'type':'date'}),
            'public_registration_open_date': TextInput(attrs={'type':'date'}),
            'public_registration_closes_date': TextInput(attrs={'type':'date'}),
            'invite_expiration_date': TextInput(attrs={'type':'date'}),
        }


class BillingPeriodInlineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BillingPeriodInlineForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = BillingPeriod
        fields = [
            'name',
            'start_date',
            'end_date',
            'invoice_date',
            'due_date',
        ]



class EventInviteEmailForm(forms.Form):
    emails = forms.CharField(
        widget=forms.Textarea,
        label="Email Addresses",
        help_text="Email addresses invites should be sent to. One per line, please.",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        
        super(EventInviteEmailForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            'emails',
            ButtonHolder(
                Submit('submit', 'Send Invites', css_class='button white')
            )
        )

    class Meta:
        fields = [ 'emails', ]
        


invite_or_user_validator = RegexValidator(r"^(invite|user)-(\d+)$", "Invalid invite or user ID")
class EventInviteAjaxForm(forms.Form):
    user_or_invite_id = forms.CharField(
        label="Invite or User ID",
        required=True,  # Note: validators are not run against empty fields
        validators=[invite_or_user_validator]
    )
