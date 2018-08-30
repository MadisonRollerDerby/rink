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
            label="",
            required=False,
        )

        self.helper.layout = Layout(
            Fieldset(
                'Details',
                'name',
                'start_date',
                'end_date',
            ),
            # If this fieldset is no longer #1, change the helper.layout[1] code below
            Fieldset(
                'Invoices and Billing',
                'automatic_billing_dates',
            ),
            Fieldset(
                'Legal Forms Required',
                'legal_forms',
            ),
            Fieldset(
                'Optional Dates',
                'public_registration_open_date',
                'public_registration_closes_date',
                'invite_expiration_date',
            ),
            Fieldset(
                'Blurbs',
                'description',
                'legal_blurb',
                'payment_blurb',
            ),
            Fieldset(
                'Settings',
                'max_capacity',
                'minimum_registration_age',
                'maximum_registration_age',
            ),

            ButtonHolder(
                Submit('submit', 'Save Event', css_class='button white')
            )
        )
        
        if self.instance.id and BillingPeriod.objects.filter(event=self.instance).count() > 0:
            # Remove the Invoice and Billing section if we already have Billing Periods
            del self.helper.layout[1]
        else:
            # Allow for the Invoices and Billing Period wizard to display in the form.
            for group in BillingGroup.objects.filter(league=league):
                field_name = 'billinggroup{}'.format(group.pk)
                self.fields[field_name] = forms.DecimalField(
                    min_value=0,
                    decimal_places=2,
                    max_digits=10,
                    label="{} Invoice Amount".format(group.name),
                    initial=group.invoice_amount,
                )
                #self.fields[field_name].widget.attrs.update({'placeholder': "0.00"})

                self.helper.layout[1].append(
                    field_name
                )

    class Meta:
        model = RegistrationEvent

        fields = [
            'name',
            'start_date',
            'end_date',
            'description',
            'legal_blurb',
            'payment_blurb',
            'public_registration_open_date',
            'public_registration_closes_date',
            'invite_expiration_date',
            'max_capacity',
            'minimum_registration_age',
            'maximum_registration_age',
            'legal_forms',
        ]
        widgets = {
            'start_date': TextInput(attrs={'type': 'date'}),
            'end_date': TextInput(attrs={'type': 'date'}),
            'public_registration_open_date': TextInput(attrs={'type': 'date'}),
            'public_registration_closes_date': TextInput(attrs={'type': 'date'}),
            'invite_expiration_date': TextInput(attrs={'type': 'date'}),
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


class BillingGroupModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        default = ""
        if obj.default_group_for_league:
            default = "*"
        return "{}{}".format(obj.name, default)


class EventInviteEmailForm(forms.Form):
    emails = forms.CharField(
        widget=forms.Textarea,
        label="Email Addresses",
        help_text="Email addresses invites should be sent to. One per line, please.",
        required=True,
    )

    def __init__(self, league, *args, **kwargs):
        super(EventInviteEmailForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        initial_value = 0
        try:
            initial_value = BillingGroup.objects.filter(
                league=league, default_group_for_league=True).get().pk
        except BillingGroup.DoesNotExist:
            pass

        self.fields['billing_group'] = BillingGroupModelChoiceField(
            queryset=BillingGroup.objects.filter(league=league),
            empty_label="Select a Billing Group",
            label="Billing Group",
            required=True,
            initial=initial_value,
        )

        self.helper.layout = Layout(
            'emails',
            'billing_group',
            ButtonHolder(
                Submit('submit', 'Send Invites', css_class='button white')
            )
        )

    class Meta:
        fields = ['emails', ]


invite_or_user_validator = RegexValidator(r"^(invite|user)-(\d+)$", "Invalid invite or user ID")


class EventInviteAjaxForm(forms.Form):
    user_or_invite_id = forms.CharField(
        label="Invite or User ID",
        required=True,  # Note: validators are not run against empty fields
        validators=[invite_or_user_validator]
    )
