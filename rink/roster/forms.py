from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field, HTML, Div
from django import forms
from django.urls import reverse

from billing.models import BillingGroup, BillingGroupMembership, Invoice
from registration.models import RegistrationEvent
from users.models import User, Tag, UserLog


class RosterProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'derby_name', 'derby_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Submit', css_class='btn-primary'))


class BillingGroupForm(forms.Form):
    def __init__(self, *args, **kwargs):
        league = kwargs.pop('league', None)
        user = kwargs.pop('user', None)

        if not league or not league:
            raise ValueError("Hey you need to pass a league and user, you knucklehead.")

        try:
            membership = BillingGroupMembership.objects.get(
                league=league,
                user=user
            )
        except BillingGroupMembership.DoesNotExist:
            billing_group = None
        else:
            billing_group = membership.group

        if not billing_group:
            try:
                default_group_for_league = BillingGroup.objects.get(
                    league=league,
                    default_group_for_league=True,
                )
            except BillingGroup.DoesNotExist:
                billing_group = None
            else:
                billing_group = default_group_for_league

        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse('roster:admin_billing_group', kwargs={'pk': user.pk})
        self.helper.form_class = 'form-inline'
        self.fields['billing_group'] = forms.ModelChoiceField(
            label="Billing Group:",
            queryset=BillingGroup.objects.filter(league=league),
            initial=billing_group,
        )
        self.helper.add_input(Submit('submit', 'Save', css_class="btn-sm ml-3"))


class RosterFilterForm(forms.Form):
    # For Invoice Admin filtering form
    filtered = forms.BooleanField(initial=True, required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        league = kwargs.pop('league', None)

        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        # TOP SEARCH DIV
        # Contains Search Box and Event Filter
        search_div = Div('search_div', css_class='filter-inline form-inline')
        # Search Box
        self.fields['search'] = forms.CharField(max_length=200, label='', required=False)
        self.fields['search'].widget.attrs.update({'placeholder': "Search - Name, Email"})
        search_div.append('search')
        # Event Dropdown
        self.fields['events'] = forms.ModelChoiceField(
            queryset=RegistrationEvent.objects.filter(league=league),
            required=False,
            label='',
        )
        search_div.append('events')
        self.helper.layout.append(search_div)

        # BILLING FILTERS DIV
        # Invoice Due / Overdue
        billing_div = Div('billing_div', css_class='filter-inline form-inline bg-light')
        self.fields['unpaid_invoice'] = forms.BooleanField(initial=False, required=False)
        billing_div.append('unpaid_invoice')
        self.fields['invoice_overdue'] = forms.BooleanField(initial=False, required=False)
        billing_div.append('invoice_overdue')
        self.helper.layout.append(billing_div)

        # USER TAGS DIV
        # User Tags, users can have multiple tags of various reasons or another
        tags = Tag.objects.filter(league=league)
        if tags.count() > 0:
            user_tags_div = Div('user_tags', css_class='filter-inline form-inline')
            user_tags_div.append(HTML('<small><mark>Tags:</mark></small>'))
            for tag in tags:
                self.fields['tag{}'.format(tag.pk)] = forms.BooleanField(label=tag.text,
                    initial=False, required=False)
                user_tags_div.append('tag{}'.format(tag.pk))
            self.helper.layout.append(user_tags_div)

        # BILLING GROUP DIV
        # Billing Group filters the are league-wide for determining billing amount
        billing_groups = BillingGroup.objects.filter(league=league)
        if billing_groups.count() > 0:
            billing_group_div = Div('billing_group', css_class='filter-inline form-inline bg-light')
            billing_group_div.append(HTML('<small><mark>Groups:</mark></small>'))
            for billing_group in billing_groups:
                self.fields['billing_group{}'.format(billing_group.pk)] = forms.BooleanField(
                    label=billing_group.name, initial=False, required=False)
                billing_group_div.append('billing_group{}'.format(billing_group.pk))
            self.helper.layout.append(billing_group_div)


class RosterAddNoteForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea)


class RosterCreateInvoiceForm(forms.ModelForm):
    send_email = forms.BooleanField(
        initial=True,
        help_text="If checked, an email will be sent to user alerting them an invoice has been created."
    )

    class Meta:
        model = Invoice
        fields = ['description', 'invoice_amount', 'invoice_date', 'due_date']
