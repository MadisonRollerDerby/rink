from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field, HTML, Div
from django import forms
from django.contrib.auth import (
    authenticate, password_validation,
)
from django.urls import reverse
from django.utils import timezone

from .models import RegistrationData
from users.models import User
from registration.models import Roster
from rink.utils.forms import get_date_months, get_date_days, get_date_years


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
        help_text="Set a password for your Rink account."
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
        event = kwargs.pop('event', None)
        if event:
            login_url = "{}?next={}".format(
                reverse('account_login'),
                reverse('register:register_event', kwargs={'league_slug': event.league.slug, 'event_slug': event.slug})
            )
        else:
            # meh... this could be better, I guess...
            login_url = reverse('account_login')

        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            'email',
            'password1',
            'password2',
            ButtonHolder(
                Submit('submit', 'Continue Registration', css_class='button white'),
                HTML('<a href="{}"><input type="button" name="button" value="Already Have an Account?" class="btn button btn-secondary" id="button-id-button"></a>'.format(login_url)),
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
    birth_day = forms.ChoiceField(widget=forms.Select(), choices=get_date_days(), required=True)
    birth_month = forms.ChoiceField(widget=forms.Select(), choices=get_date_months(), required=True)
    birth_year = forms.ChoiceField(widget=forms.Select(), choices=get_date_years(), required=True)

    def __init__(self, *args, **kwargs):
        self.logged_in_user_id = kwargs.pop('logged_in_user_id', None)
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)

        #for field_name, field in self.fields.items():
        #    field.widget.attrs['placeholder'] = field.label

        self.fields['stripe_token'] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
        )
        self.fields['emergency_date_of_birth'].widget = forms.HiddenInput()

        if kwargs.get('instance', None):
            self.fields['birth_month'].initial = kwargs['instance'].emergency_date_of_birth.month
            self.fields['birth_day'].initial = kwargs['instance'].emergency_date_of_birth.day
            self.fields['birth_year'].initial = kwargs['instance'].emergency_date_of_birth.year

        self.fields['birth_month'].label = ""
        self.fields['birth_day'].label = ""
        self.fields['birth_year'].label = ""

        self.helper.form_show_labels = True
        self.helper.form_tag = False
        self.helper.layout = Layout()
        self.helper.layout.append(
            Fieldset(
                'Skater Details',
                'contact_email',
                'contact_first_name',
                'contact_last_name',
                'contact_address1',
                'contact_address2',
                'contact_city',
                'contact_state',
                'contact_zipcode',
                'contact_phone',
            )
        )

        if self.event.form_type == "minor":
            self.fields['parent1_address_same'] = forms.BooleanField(
                label="Lives at Same Address as Skater",
                initial=True,
            )
            self.fields['parent2_address_same'] = forms.BooleanField(
                label="Lives at Same Address as Skater",
                initial=True,
            )
            self.helper.layout.append(
                Fieldset(
                    'Primary Parent/Guardian',
                    Field('parent1_name', required=True),
                    Field('parent1_relationship', required=True, placeholder="Mother, Father, etc."),
                    Field('parent1_email', required=True),
                    Field('parent1_phone', required=True),
                    'parent1_address_same',
                    'parent1_address1',
                    'parent1_address2',
                    'parent1_city',
                    'parent1_state',
                    'parent1_zipcode',
                )
            )
            self.helper.layout.append(
                Fieldset(
                    'Second Parent/Guardian (Optional)',
                    Field('parent2_name', placeholder="Optional"),
                    Field('parent2_relationship', placeholder="Optional - Mother, Father, etc."),
                    Field('parent2_email', placeholder="Optional"),
                    Field('parent2_phone', placeholder="Optional"),
                    'parent2_address_same',
                    'parent2_address1',
                    'parent2_address2',
                    'parent2_city',
                    'parent2_state',
                    'parent2_zipcode',
                )
            )

        if self.event.form_type == "minor":
            self.helper.layout.append(
                Fieldset(
                    'Derby Details',
                    'derby_name',
                    'derby_number',
                    'derby_pronoun',
                )
            )
        else:
            self.helper.layout.append(
                Fieldset(
                    'Derby Details',
                    'derby_name',
                    'derby_number',
                    'derby_insurance_type',
                    'derby_insurance_number',
                    'derby_pronoun',
                )
            )

        self.helper.layout.append(
            Fieldset(
                'Emergency Details',
                Div(
                    HTML('<label for="id_birth_month" class="col-form-label requiredField">Birth Date:</label>')
                ),
                Div(
                    Div(Field('birth_month'), css_class="col", style="max-width:120px;"),
                    Div(Field('birth_day'), css_class="col", style="max-width:120px;"),
                    Div(Field('birth_year'), css_class="col", style="max-width:120px;"),
                    css_class="form-row",
                ),
                'emergency_contact',
                'emergency_phone',
                'emergency_relationship',
                'emergency_hospital',
                'emergency_allergies',
            )
        )

        self.helper.layout.append('stripe_token')
        self.helper.layout.append('emergency_date_of_birth')

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

            'parent1_email',
            'parent1_phone',
            'parent1_relationship',
            'parent1_name',
            'parent1_address1',
            'parent1_address2',
            'parent1_city',
            'parent1_state',
            'parent1_zipcode',

            'parent2_email',
            'parent2_phone',
            'parent2_relationship',
            'parent2_name',
            'parent2_address1',
            'parent2_address2',
            'parent2_city',
            'parent2_state',
            'parent2_zipcode',

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

    def clean_contact_email(self):
        if self.logged_in_user_id:
            existing_user = User.objects.exclude(
                pk=self.logged_in_user_id).filter(email=self.cleaned_data['contact_email'])
        else:
            existing_user = User.objects.filter(email=self.cleaned_data['contact_email'])

        if existing_user.exists():
            raise forms.ValidationError("This email address already has an account set up. You cannot change your email address to it.", code="username_conflict")

        return self.cleaned_data['contact_email']

    def update_user(self, user):
        user.first_name = self.cleaned_data['contact_first_name']
        user.last_name = self.cleaned_data['contact_last_name']
        user.email = self.cleaned_data['contact_email']
        user.derby_name = self.cleaned_data['derby_name']
        user.derby_number = self.cleaned_data['derby_number']
        user.save()

    def create_roster(self, user, event):
        return Roster.objects.create(
            user=user,
            event=event,
            first_name=self.cleaned_data['contact_first_name'],
            last_name=self.cleaned_data['contact_last_name'],
            email=self.cleaned_data['contact_email'],
            derby_name=self.cleaned_data['derby_name'],
            derby_number=self.cleaned_data['derby_number'],
        )


class LegalDocumentAgreeForm(forms.Form):
    legal_agree = forms.BooleanField(required=True)


class LegalDocumentInitialsForm(forms.Form):
    legal_initials_guardian = forms.CharField(
        required=True,
        max_length=3,
        min_length=2,
    )

    legal_initials_participant = forms.CharField(
        required=True,
        max_length=3,
        min_length=2,
    )
