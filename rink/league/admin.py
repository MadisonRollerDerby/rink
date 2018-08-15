from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import (
    Organization, League, InsuranceType
)


class OrganizationAdmin(GuardedModelAdmin):
    pass

class LeagueAdmin(GuardedModelAdmin):
    pass

admin.site.register(Organization, OrganizationAdmin)
admin.site.register(League, LeagueAdmin)
admin.site.register(InsuranceType)


from django.contrib.auth.models import Permission
admin.site.register(Permission)
