from django.urls import path

from . import views

app_name = 'billing'
urlpatterns = [
    path('admin', views.BillingAdminView.as_view(), name="billing_admin"),
    path('pay', views.PayView.as_view(), name="pay"),
    path('payments', views.PaymentHistoryView.as_view(), name="payment_history"),
    path('update-card', views.UpdateUserStripeCardView.as_view(), name="update_card"),

]
