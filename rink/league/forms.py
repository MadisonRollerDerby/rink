from django.conf import settings
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from guardian.shortcuts import get_perms_for_model, get_user_perms, \
    assign_perm, remove_perm
import re

from .models import Organization, League
from users.models import User


class LeagueSettingsBaseForm(object):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super().__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', 'Submit'))


class LeagueNameForm(LeagueSettingsBaseForm, forms.ModelForm):
    class Meta:
        model = League
        fields = [
            'name',
            'logo',
            'short_name',
        ]


class LeagueBillingForm(LeagueSettingsBaseForm, forms.ModelForm):
    class Meta:
        model = League
        fields = [
            'default_payment_due_day',
            'default_invoice_day_diff',
            'stripe_private_key',
            'stripe_public_key',
        ]


class LeagueRegistrationForm(LeagueSettingsBaseForm, forms.ModelForm):
    class Meta:
        model = League
        fields = [
            'default_address_state',
            'default_insurance_type',
        ]


class LeagueEmailForm(LeagueSettingsBaseForm, forms.ModelForm):
    class Meta:
        model = League
        fields = [
            'email_from_name',
            'email_from_address',
            'email_cc_address',
            'email_header',
            'email_footer',
        ]


class PermissionsForm(forms.Form):
    def __init__(self, request_user, editing_user, organization=None, league=None, *args, **kwargs):
        self.organization = organization  # current organization we are editing
        self.league = league  # league we are editing if on non-org-admin page
        self.request_user = request_user  # user requesting this page
        self.editing_user = editing_user  # user we are editing
        self.regex = re.compile('^(org|league)(\d+)\_([A-Za-z0-9_]+)$') 
        self.helper = FormHelper()
        super(PermissionsForm, self).__init__(*args, **kwargs)

        if not self.organization and not self.league:
            raise ValidationError("Both organization and league cannot be empty.")
        if not self.organization:
            self.organization = self.league.organization
        # If leagues is left blank, we assume we are probably wanting to grab
        # from all the leagues under the specified organization. The way this is
        # setup could be confusing, I guess if you want to REALLY use it wrong.
        # if not self.league:
        #    pass

        leagues = None

        # First, check if the current editing user has priviliges to edit
        # users is this organization.
        if self.request_user.has_perm("league:org_admin", self.organization):
            user_organization_perms = get_user_perms(self.editing_user, organization)

            self.organization_permissions = []
        
            # Get available permissions for both organizaiton and league models
            for permission in get_perms_for_model(Organization):
                if permission.codename not in settings.RINK_PERMISSIONS_IGNORE:
                    self.organization_permissions.append(permission)

            # Dynamically create inputs for each organization and league permissions
            for permission in self.organization_permissions:
                initial = False
                if permission.codename in user_organization_perms:
                    initial = True

                self.fields["{}{}_{}".format("org", organization.pk, permission.codename)] = forms.BooleanField(
                    label="{} - {}".format(organization, permission.name),
                    required=False,
                    initial=initial,
                )

            # Since we are a super admin, use all the leagues in our current org
            leagues = League.objects.filter(organization=organization)

        # Next, if we are a user who only has access to a league (not an organization)
        # only allow them to change permissions for that league.
        elif self.league and self.request_user.has_perm("league:league_admin", self.league):
            leagues = League.objects.filter(pk=self.league.pk)

        # Apparently you are not any kind of admin. Bye!
        else:
            raise PermissionDenied("You don't seem to be an admin of an organization or league. #88")

        self.league_permissions = []
        for permission in get_perms_for_model(League):
            if permission.codename not in settings.RINK_PERMISSIONS_IGNORE:
                self.league_permissions.append(permission)


        for league in leagues:
            user_league_permissions = get_user_perms(self.editing_user, league)

            for permission in self.league_permissions:
                initial = False
                if permission.codename in user_league_permissions:
                    initial = True

                self.fields["{}{}_{}".format("league", league.pk, permission.codename)] = forms.BooleanField(
                    label="{} - {}".format(league, permission.name),
                    required=False,
                    initial=initial,
                )
        self.helper.add_input(Submit('submit', 'Submit'))


    def clean(self):
        cleaned_data = super(PermissionsForm, self).clean()

        # Check that all organizations and leagues are valid and the user adding
        # these permissions has access to them. Some of this happens in the views
        # but we're going to do it here because I am thinking about it now.
        for key, value in cleaned_data.items():
            match = self.regex.match(key)
            if match:
                permissions = None

                # Check that organization matches the one submitted to the form.
                # Check that permission is available for the organization model.
                if match.group(1) == "org":
                    if self.organization.pk != int(match.group(2)):
                        raise ValidationError("Current organization ID ({}) does not match submitted organization ID ({})".format(self.organization.pk, match.group(2)))

                    # Check league belongs to organization and has these permissions.
                    permissions = get_perms_for_model(Organization)

                    # Check that we have permissions to modify this organization.
                    if not self.request_user.has_perm("league:org_admin", self.organization):
                        raise PermissionDenied("You don't seem to be an admin of an organization or league. #133")
                
                elif match.group(1) == "league":
                    try:
                        league = League.objects.get(pk=int(match.group(2)))
                    except League.DoesNotExist:
                        raise ValidationError("League with ID #{} does not exist.".format(match.group(2)))

                    if league.organization != self.organization:
                        raise ValidationError("League with ID #{} does not belong to organization '{}'.".format(match.group(2), self.organization))

                    # Check that permission is availavle for the league model.
                    permissions = get_perms_for_model(League)

                    # Check that we have permissions to modify this organization.
                    if not self.request_user.has_perm("league:org_admin", league.organization) and \
                       not self.request_user.has_perm("league:league_admin", league):
                        raise PermissionDenied("You don't seem to be an admin of an organization or league. #151")
                
                # Actually check if the permissions here are valid for the model we are checking.
                if permissions:
                    permission_list = []
                    for permission in permissions:
                        permission_list.append(permission.codename)
                    if match.group(3) not in permission_list:
                        raise ValidationError("Permission '{}' does not appear to be part of that model.".format(match.group(3)))   

        return cleaned_data


    def save_permissions(self):
        for key, value in self.cleaned_data.items():
            match = self.regex.match(key)
            if match:
                obj = None
                if match.group(1) == "org":
                    obj = self.organization  # this is OK, value is checked in clean()
                elif match.group(1) == "league":
                    obj = League.objects.get(pk=int(match.group(2)))

                if obj and value:
                    assign_perm(match.group(3), self.editing_user, obj)
                elif obj and not value:
                    remove_perm(match.group(3), self.editing_user, obj)


class CreateRinkUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 
            'last_name', 
            'derby_name',
            'email', 
        ]

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super(CreateRinkUserForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', 'Submit'))
