from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.generic.edit import CreateView, UpdateView
from django.views import View

from guardian.shortcuts import get_perms_for_model, get_users_with_perms

from users.models import User

from .forms import (LeagueNameForm, LeagueBillingForm, LeagueRegistrationForm,
    LeagueEmailForm, PermissionsForm, CreateRinkUserForm)
from .models import League, Organization
from .mixins import RinkOrgAdminPermissionRequired, RinkLeagueAdminPermissionRequired
from league.utils import send_email
from users.models import User


class LeagueAdminList(RinkOrgAdminPermissionRequired, View):
    def get(self, request, organization_slug):
        return render(request, 'league/league_list.html', {
                # Filter by the current organization to ensure we have permission
                'leagues': League.objects.filter(organization=request.user.organization),
            }
        )  


class LeagueAdminCreate(RinkOrgAdminPermissionRequired, CreateView):
    model = League
    form_class = LeagueNameForm
    template_name = 'league/league_detail.html'

    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        return super().form_valid(form)


class LeagueAdminUpdate(RinkLeagueAdminPermissionRequired, View):
    # This class is a mess and could be cleaned up
    template_name = 'league/league_detail.html'

    def get(self, request, organization_slug, slug):
        league = get_object_or_404(League, slug=slug)

        warning = ''
        if not league.stripe_private_key or not league.stripe_public_key:
            warning = '<strong>WARNING:</strong> Both <strong>Stripe Public Key</strong> and <strong>Stripe Secret Key</strong> need to be set in the Billing section to process credit card payments.'

        return render(request, self.template_name, {
            'league': league,
            'forms': {
                'name_form': LeagueNameForm(instance=league),
                'billing_form': LeagueBillingForm(instance=league),
                'registration_form': LeagueRegistrationForm(instance=league),
                'email_form': LeagueEmailForm(instance=league),
            },
            'warning': warning,
        })

    def post(self, request, organization_slug, slug):
        league = get_object_or_404(League, slug=slug)
        forms = {
            'name_form': LeagueNameForm(request.POST, instance=league),
            'billing_form': LeagueBillingForm(request.POST, instance=league),
            'registration_form': LeagueRegistrationForm(request.POST, instance=league),
            'email_form': LeagueEmailForm(request.POST, instance=league),
        }
        
        for form in forms:
            if forms[form].is_valid():
                forms[form].save()
                messages.success(request, 'Saved League Settings')
                return HttpResponseRedirect(reverse("league:league_update",
                    kwargs={'slug': league.slug, 'organization_slug': league.organization.slug}))
        return render(request, self.template_name, {
            'forms': forms,
            'league': league,
        })


class OrganizationPermissionsView(RinkOrgAdminPermissionRequired, View):
    def get(self, request, organization_slug):
        organization = get_object_or_404(Organization, slug=organization_slug)
        leagues = League.objects.filter(organization=request.user.organization)

        # Get all users with admin privileges for this organization.
        organization_permissions_filtered = []

        for permission in get_perms_for_model(Organization):
            if permission.codename not in settings.RINK_PERMISSIONS_IGNORE:
                organization_permissions_filtered.append(permission.codename)

        organization.users = get_users_with_perms(organization, 
            attach_perms=True,
            only_with_perms_in=organization_permissions_filtered
        )


        # Get all users with admin priveleges for all leagues under this
        # organization.
        league_permissions_filtered = []
        for permission in get_perms_for_model(League):
            if permission.codename not in settings.RINK_PERMISSIONS_IGNORE:
                league_permissions_filtered.append(permission.codename)

        for league in leagues:
            league.users = get_users_with_perms(league, 
                attach_perms=True,
                only_with_perms_in=league_permissions_filtered
            )


        return render(request, 'league/permissions_list.html', {
                'organization': organization,
                'leagues': leagues,
                'ignore': settings.RINK_PERMISSIONS_IGNORE,
            }
        )


class OrganizationPermissionsChange(RinkOrgAdminPermissionRequired, View):
    def get(self, request, organization_slug, user_id):
        organization = get_object_or_404(Organization, slug=organization_slug)
        user = get_object_or_404(User, pk=user_id)

        form = PermissionsForm(
            organization=organization,
            request_user=request.user,
            editing_user=user,
        )

        return render(request, 'league/permissions_change.html', {
                'form': form,
                'user': user,
            }
        )

    def post(self, request, organization_slug, user_id):
        organization = get_object_or_404(Organization, slug=organization_slug)
        user = get_object_or_404(User, pk=user_id)

        form = PermissionsForm(
            data=request.POST,
            organization=organization, 
            request_user=request.user,
            editing_user=user,
        )
        if form.is_valid():
            form.save_permissions()
            return HttpResponseRedirect(reverse("league:organization_permissions", kwargs={'organization_slug':organization.slug}))
        
        # TODO display errors
        #else:
        #    print(form.non_field_errors())


class CreateUserView(RinkOrgAdminPermissionRequired, View):
    template = "league/create_rink_user.html"
    def get(self, request, organization_slug):
        return render(request, self.template, {'form': CreateRinkUserForm()})


    def post(self, request, organization_slug):
        form = CreateRinkUserForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data

            # Yeah I guess... this could be something more custom.
            organization = Organization.objects.get(pk=request.session['view_organization'])
            league = League.objects.get(pk=request.session['view_league'])

            password = get_random_string(12)
            user = User.objects.create_user(
                email = cleaned_data['email'],
                password = password,
            )

            user.first_name = cleaned_data['first_name']
            user.last_name = cleaned_data['last_name']
            user.derby_name = cleaned_data['derby_name']

            # These two might make more sense elsewhere as an item on the
            # form or validating that they are allowed to access it.
            user.organization = organization
            user.league = league
            user.save()

            send_email(
                league = league,
                to_email = cleaned_data['email'],
                template = "admin_user_creation_invite",
                context = {
                    'user': user,
                    'password': password,
                    'league': league,
                    'organization': organization,
                }
            )

            return HttpResponseRedirect(
                reverse("league:organization_permissions_update", 
                    kwargs = {
                        'organization_slug': organization.slug,
                        'user_id': user.pk,
                    }
                )
            )

        else:
            return render(request, self.template, {'form': form})

