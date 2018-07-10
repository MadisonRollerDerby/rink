from django.contrib import admin
from .models import BillingStatus, BillingPeriod

admin.site.register(BillingStatus)
admin.site.register(BillingPeriod)
