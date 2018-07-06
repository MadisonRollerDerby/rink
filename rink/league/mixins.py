from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import get_object_or_404

from guardian.core import ObjectPermissionChecker

from .models import Organization


class OrganizationAdminRequiredMixIn(object):
    """
    Check that a user has administration permissions for the current organization.
    Requires organization_slug to be passed in the URL.

    Return 403 if they don't have access.
    Returns 404 if the object doesn't exist.
    Returns impoperly configured if the organization slug isn't in the URL args.
    """

    def dispatch(self, request, *args, **kwargs):
        # Raise ImproperlyConfigured if organization slug is not sent in the URL
        organization_slug = kwargs.get('organization_slug', None)
        if organization_slug is None:
            raise ImproperlyConfigured("URL does not have an organization_slug, can't determine permissions or organization object.")

        # Raise 404 if object is not found
        organization = get_object_or_404(Organization, slug=organization_slug)

        # Check if the user has admin access to this organization, if not, raise
        # that they don't have access.
        checker = ObjectPermissionChecker(request.user)
        if checker.has_perm('org_admin', organization):
            return super(OrganizationAdminRequiredMixIn, self).dispatch(request, *args, **kwargs)

        raise PermissionDenied