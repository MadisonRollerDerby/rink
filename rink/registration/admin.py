from django.contrib import admin
from .models import RegistrationInvite, RegistrationEvent, RegistrationData, Roster

admin.site.register(RegistrationInvite)
admin.site.register(RegistrationEvent)
admin.site.register(RegistrationData)
admin.site.register(Roster)