from django.urls import path

from . import views

app_name = 'registration'
urlpatterns = [
    #path('', views.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    
    path(
        '<slug:registration_slug>/<uuid:invite_key>', 
        views.RegistrationBegin.as_view(), 
        name="registration-slug-invite",
    ),

    path(
        '<slug:registration_slug>', 
        views.RegistrationBegin.as_view(),
        name="registration-slug",
    ),


    # Event List
    path('', 
        views.EventAdminList.as_view(), 
        name="event_admin_list"
    ),
    # Event Creation
    path('new',
        views.EventAdminCreate.as_view(),
        name="event_admin_create"
    ),

    # Event Settings
    path('<slug:event_slug>/settings', 
        views.EventAdminSettings.as_view(),
        name="event_admin_settings"
    ),

    # Event Invites
    path('<slug:event_slug>/invites', 
        views.EventAdminInvites.as_view(),
        name="event_admin_invites"
    ),

    # Event Roster
    path('<slug:event_slug>/roster', 
        views.EventAdminRoster.as_view(),
        name="event_admin_roster"
    ),

    # Event Billing Periods
    path('<slug:event_slug>/billing', 
        views.EventAdminBillingPeriods.as_view(),
        name="event_admin_billing_periods"
    ),

]