from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views import View

from guardian.shortcuts import get_perms_for_model, get_users_with_perms

from users.models import User

from .forms import LeagueForm, PermissionsForm
from .models import League, Organization
from .utils import OrganizationAdminRequiredMixIn


class LeagueAdminList(OrganizationAdminRequiredMixIn, View):
    def get(self, request, organization_slug):
        return render(request, 'league/league_list.html', {
                # Filter by the current organization to ensure we have permission
                'leagues': League.objects.filter(organization=request.user.organization),
            }
        )  


class LeagueAdminCreate(OrganizationAdminRequiredMixIn, CreateView):
    model = League
    form_class = LeagueForm
    template_name = 'league/league_detail.html'

    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        return super().form_valid(form)


class LeagueAdminUpdate(OrganizationAdminRequiredMixIn, UpdateView):
    model = League
    form_class = LeagueForm
    template_name = 'league/league_detail.html'



class OrganizationPermissionsView(OrganizationAdminRequiredMixIn, View):
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


class OrganizationPermissionsChange(OrganizationAdminRequiredMixIn, View):
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

