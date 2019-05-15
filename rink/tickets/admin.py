from django.contrib import admin
from .models import (
    TicketPurchase, TicketEvent
)

admin.site.register(TicketPurchase)
admin.site.register(TicketEvent)
