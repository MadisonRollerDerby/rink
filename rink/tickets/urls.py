from django.urls import path

from . import views

app_name = 'tickets'
urlpatterns = [
    path(
        '<slug:league_slug>/<slug:event_slug>',
        views.TicketPurchaseView.as_view(),
        name="ticket_purchase",
    ),

    path(
        '<slug:league_slug>/<slug:event_slug>/done',
        views.TicketPurchaseDoneView.as_view(),
        name="ticket_purchase_done",
    ),
]
