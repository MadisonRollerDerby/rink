from django.contrib import messages
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field, HTML
from crispy_forms.bootstrap import FormActions
from django import forms
from django.contrib.auth import (
    authenticate, password_validation,
)
from django.forms.widgets import CheckboxSelectMultiple
from django.urls import reverse

from guardian.shortcuts import assign_perm

from legal.models import LegalDocument
from users.models import User
from .models import RegistrationData, RegistrationEvent


class RegistrationSignupForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email Address",
        required=True,
        widget=forms.TextInput(attrs={
            'type': 'email', 
            'placeholder': 'Email Address'
        })
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
        help_text=""
    )

    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Enter the same password as before, for verification.",
    )

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super(RegistrationSignupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            'email',
            'password1',
            'password2',
            ButtonHolder(
                Submit('submit', 'Continue Registration', css_class='button white')
            )
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password2', error)

    def save(self, league, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.league = league
        user.organization = league.organization
        if commit:
            user.save()
        return user


class RegistrationDataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.logged_in_user_id = kwargs.pop('logged_in_user_id', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper(self)

        #for field_name, field in self.fields.items():
        #    field.widget.attrs['placeholder'] = field.label

        self.fields['stripe_token'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
        )

        self.helper.form_show_labels = True
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Contact Details',
                'contact_email',
                'contact_first_name',
                'contact_last_name',
                'contact_address1',
                'contact_address2',
                'contact_city',
                'contact_state',
                'contact_zipcode',
                'contact_phone',
            ),
            Fieldset(
                'Derby Details',
                'derby_name',
                'derby_number',
                'derby_insurance_type',
                'derby_insurance_number',
                'derby_pronoun',
            ),
            Fieldset(
                'Emergency Details',
                'emergency_date_of_birth',
                'emergency_contact',
                'emergency_phone',
                'emergency_relationship',
                'emergency_hospital',
                'emergency_allergies',
            ),
            'stripe_token',
        )

    class Meta:
        model = RegistrationData
        fields = [
            'contact_email',
            'contact_first_name',
            'contact_last_name',
            'contact_address1',
            'contact_address2',
            'contact_city',
            'contact_state',
            'contact_zipcode',
            'contact_phone',

            'derby_name',
            'derby_number',
            'derby_insurance_type',
            'derby_insurance_number',
            'derby_pronoun',

            'emergency_date_of_birth',
            'emergency_contact',
            'emergency_phone',
            'emergency_relationship',
            'emergency_hospital',
            'emergency_allergies',
        ]

        widgets = {
            'emergency_date_of_birth': forms.DateInput(format=('%-m/%-d/%Y'), attrs={'class': 'datepicker'}),
        }

    def clean_contact_email(self):
        if self.logged_in_user_id:
            existing_user = User.objects.exclude(
                pk=self.logged_in_user_id).filter(email=self.cleaned_data['contact_email'])
        else:
            existing_user = User.objects.filter(email=self.cleaned_data['contact_email'])

        if existing_user.exists():
            raise forms.ValidationError("This email address already has an account set up. You cannot change your email address to it.", code="username_conflict")

        return self.cleaned_data['contact_email']


class LegalDocumentAgreeForm(forms.Form):
    legal_agree = forms.BooleanField(required=True)
