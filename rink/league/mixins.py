from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import render, get_object_or_404

from league.models import Organization, League


class RinkOrgAdminPermissionRequired(object):
    _base_organization_permissions = ['org_admin']
    _base_league_permissions = []
    organization_permissions = []
    league_permissions = []

    def dispatch(self, request, *args, **kwargs):
        try:
            self.organization = get_object_or_404(Organization, pk=request.session['view_organization'])
            self.league = get_object_or_404(League, pk=request.session['view_league'])
        except KeyError:
            raise PermissionDenied

        combined_organization_permissions = self._base_organization_permissions + self.organization_permissions
        combined_league_permissions = self._base_league_permissions + self.league_permissions

        # https://stackoverflow.com/questions/24270711/checking-if-two-lists-share-at-least-one-element
        if any(x in combined_organization_permissions for x in request.session['organization_permissions']) \
                or any(x in combined_league_permissions for x in request.session['league_permissions']):
            return super(RinkOrgAdminPermissionRequired, self).dispatch(request, *args, **kwargs)

        raise PermissionDenied


class RinkLeagueAdminPermissionRequired(RinkOrgAdminPermissionRequired):
    _base_league_permissions = ['league_admin']