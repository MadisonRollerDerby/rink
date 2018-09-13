from django.urls import path

from . import views

app_name = 'roster'
urlpatterns = [
    #path('admin', views_admin.BillingAdminView.as_view(), name="billing_admin"),
    #path('admin/<int:pk>', views_admin.BillingAdminDetailView.as_view(), name="billing_admin_detail"),

    path('', views.RosterList.as_view(), name="list"),

    path('<int:pk>/profile', views.RosterAdminProfile.as_view(), name="admin_profile"),
    path('<int:pk>/events', views.RosterAdminEvents.as_view(), name="admin_events"),

    path('<int:pk>/billing', views.RosterAdminBilling.as_view(), name="admin_billing"),
    path('<int:pk>/billing/<int:invoice_id>', views.RosterAdminBilling.as_view(), name="admin_billing_invoice"),
    path('<int:pk>/billing/new', views.RosterAdminCreateInvoice.as_view(), name="admin_billing_create"),
    path('<int:pk>/billing/group', views.RosterAdminBillingGroup.as_view(), name="admin_billing_group"),

    path('<int:pk>/subscriptions', views.RosterAdminSubscriptionsList.as_view(), name="admin_subscriptions"),
    path('<int:pk>/subscriptions/deactivate/<int:subscription_id>', views.RosterAdminSubscriptionsDeactivate.as_view(), name="admin_subscription_deactivate"),

    path('<int:pk>/legal', views.RosterAdminLegal.as_view(), name="admin_legal"),
    path('<int:pk>/tags', views.RosterAdminTags.as_view(), name="admin_tags"),

    path('<int:pk>/notes', views.RosterAdminUserLog.as_view(), name="admin_notes"),
    path('<int:pk>/notes/add', views.RosterAdminAddMessageUserLog.as_view(), name="admin_notes_add"),

    path('<int:pk>/membership', views.RosterAdminMembership.as_view(), name="admin_membership"),
    path('<int:pk>/membership/removeroster', views.RosterAdminRemoveFromRoster.as_view(), name="admin_membership_remove_roster"),
    path('<int:pk>/membership/deactivate', views.RosterAdminDeactivateUser.as_view(), name="admin_membership_make_inactive"),
    path('<int:pk>/membership/deleteuser', views.RosterAdminDeleteUser.as_view(), name="admin_membership_remove_user"),
]
