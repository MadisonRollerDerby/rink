from django.urls import path

from . import views
from . import views_admin

app_name = 'billing'
urlpatterns = [
    path('admin', views_admin.BillingAdminView.as_view(), name="billing_admin"),
    path('admin/<int:pk>', views_admin.BillingAdminDetailView.as_view(), name="billing_admin_detail"),
    path('admin/<int:pk>/payment',
        views_admin.BillingAdminAddPaymentView.as_view(), name="billing_admin_add_payment"),
    path('admin/<int:pk>/refund', 
        views_admin.BillingAdminRefundPaymentView.as_view(), name="billing_admin_refund_payment"),
    path('admin/<int:pk>/edit', 
        views_admin.BillingAdminEditInvoiceView.as_view(), name="billing_admin_edit_invoice"),

    path('pay', views.PayView.as_view(), name="pay"),
    path('payments', views.PaymentHistoryView.as_view(), name="payment_history"),
    path('update-card', views.UpdateUserStripeCardView.as_view(), name="update_card"),

]
