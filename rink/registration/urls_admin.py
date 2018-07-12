from django.urls import path

from . import views
from . import views_admin

app_name = 'registration'
urlpatterns = [
    #path('', views_admin.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views_admin.DetailView.as_view(), name='detail'),
    
    # ADMIN URLS


    # Event List
    path('', 
        views_admin.EventAdminList.as_view(), 
        name="event_admin_list"
    ),
    # Event Creation
    path('new',
        views_admin.EventAdminCreate.as_view(),
        name="event_admin_create"
    ),

    # Event Settings
    path('<slug:event_slug>/settings', 
        views_admin.EventAdminSettings.as_view(),
        name="event_admin_settings"
    ),

    # Event Invites List
    path('<slug:event_slug>/invites', 
        views_admin.EventAdminInvites.as_view(),
        name="event_admin_invites"
    ),

    # Event Invites Users Invites
    path('<slug:event_slug>/invite/users', 
        views_admin.EventAdminInviteUsers.as_view(),
        name="event_admin_invite_users"
    ),

    # Event Invites Emails Invite
    path('<slug:event_slug>/invite/emails', 
        views_admin.EventAdminInviteEmails.as_view(),
        name="event_admin_invite_emails"
    ),

    # Event Roster
    path('<slug:event_slug>/roster', 
        views_admin.EventAdminRoster.as_view(),
        name="event_admin_roster"
    ),

    # Event Billing Periods
    path('<slug:event_slug>/billing', 
        views_admin.EventAdminBillingPeriods.as_view(),
        name="event_admin_billing_periods"
    ),

]