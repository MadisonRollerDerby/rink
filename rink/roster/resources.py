from import_export import resources
from users.models import User


class RosterResource(resources.ModelResource):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'derby_name',
            'derby_number',
        ]
