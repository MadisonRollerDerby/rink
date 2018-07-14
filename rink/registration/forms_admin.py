from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field, HTML
from django import forms
from django.core.validators import RegexValidator
from django.forms import TextInput, NumberInput

from billing.models import BillingPeriod, BillingGroup
from legal.models import LegalDocument
from .models import RegistrationEvent

from decimal import Decimal


AUTOMATIC_BILLING_CHOICES = (
    ('monthly', 'Bill Monthly'),
    ('once', 'Bill Only Once'),
    ('', 'None - Custom'),
)


class RegistrationAdminEventForm(forms.ModelForm):
    automatic_billing_dates = forms.ChoiceField(
        label="Create automatic billing dates?",
        choices=AUTOMATIC_BILLING_CHOICES,
        required=False,
    )

    def __init__(self, league, *args, **kwargs):
        super(RegistrationAdminEventForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        self.fields['legal_forms'] = forms.ModelMultipleChoiceField(
            widget=forms.CheckboxSelectMultiple, 
            queryset=LegalDocument.objects.filter(league=league),
            #empty_label=None,
            label="",
            required=False,
        )

        self.helper.layout = Layout(
            HTML('<hr>'),
            Fieldset(
                'Details',
                'name',
                'start_date',
                'end_date',
            ),
            HTML('<hr>'),
            # If this fieldset is no longer #3, change the code below.
            Fieldset(
                'Invoices and Billing',
                'automatic_billing_dates',
            ),
            HTML('<hr>'),
            Fieldset(
                'Legal Forms Required',
                'legal_forms',
            ),
            HTML('<hr>'),
            Fieldset(
                'Optional Dates',
                'public_registration_open_date',
                'public_registration_closes_date',
                'invite_expiration_date',
            ),
            HTML('<hr>'),
            Fieldset(
                'Settings',
                'minimum_registration_age',
                'maximum_registration_age',
            ),
            HTML('<hr>'),

            ButtonHolder(
                Submit('submit', 'Save Event', css_class='button white')
            )
        )

        for group in BillingGroup.objects.filter(league=league):
            field_name = 'billinggroup{}'.format(group.pk)
            self.fields[field_name] = forms.DecimalField(
                min_value=0,
                decimal_places=2,
                max_digits=10,
                label="{} Invoice Amount".format(group.name),
            )
            self.fields[field_name].widget.attrs.update({'placeholder': "0.00"})

            self.helper.layout[3].append(
                field_name
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
            'legal_forms',
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
