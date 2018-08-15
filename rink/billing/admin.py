from django.contrib import admin
from .models import (
    BillingPeriod, BillingGroup, BillingPeriodCustomPaymentAmount,
    BillingGroupMembership, BillingSubscription, Invoice, Payment,
    UserStripeCard
)

admin.site.register(BillingGroup)
admin.site.register(BillingPeriod)
admin.site.register(BillingPeriodCustomPaymentAmount)
admin.site.register(BillingGroupMembership)
admin.site.register(BillingSubscription)
admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(UserStripeCard)
