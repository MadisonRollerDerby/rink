from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Field, HTML
from django import forms
from django.urls import reverse

from billing.models import BillingGroup, BillingGroupMembership
from users.models import User


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