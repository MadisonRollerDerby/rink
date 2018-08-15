from import_export import resources
from .models import Roster


class RosterResource(resources.ModelResource):
    class Meta:
        model = Roster
        exclude = ['id', 'user', 'event']