from django.contrib import admin
from .models import BillingPeriod, BillingGroup, BillingPeriodCustomPaymentAmount

admin.site.register(BillingGroup)
admin.site.register(BillingPeriod)
admin.site.register(BillingPeriodCustomPaymentAmount)
