from django.core.exceptions import PermissionDenied, ImproperlyConfigured


class RinkPermissionRequiredMixIn(object):
    def dispatch(self, request, *args, **kwargs):
        self.organization_permissions = getattr(self, 'organization_permissions', [])
        self.league_permissions = getattr(self, 'league_permissions', [])
        if not self.organization_permissions and not self.league_permissions:
            raise ImproperlyConfigured("RinkPermissionRequiredMixIn requires either/both organization_permissions or league_permissions to be set.")

        # https://stackoverflow.com/questions/24270711/checking-if-two-lists-share-at-least-one-element
        if any(x in self.organization_permissions for x in request.session['organization_permissions']) or any(x in self.league_permissions for x in request.session['league_permissions']):
            return super(RinkPermissionRequiredMixIn, self).dispatch(request, *args, **kwargs)

        raise PermissionDenied



"""
Here's a couple permission mixins for easily setting the org/league permissions
on a class based view.
"""

class OrganizationAdminRequiredMixIn(RinkPermissionRequiredMixIn):
    organization_permissions = ['org_admin']

class LeagueAdminRequiredMixIn(RinkPermissionRequiredMixIn):
    organization_permissions = ['org_admin']
    league_permissions = ['league_admin']