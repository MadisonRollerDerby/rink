from import_export import resources
from registration.models import RegistrationData


class RosterResource(resources.ModelResource):
    class Meta:
        model = RegistrationData
        exclude = ['invite', 'user', 'event', 'roster', 'billing_subscription', 'legal_forms', 'organization', ]
