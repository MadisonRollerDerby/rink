from django.urls import path

from . import views

app_name = 'register'
urlpatterns = [
    path(
        '<slug:league_slug>/<slug:event_slug>/<uuid:invite_key>/',
        views.RegisterBegin.as_view(),
        name="register_event_uuid",
    ),

    path(
        '<slug:league_slug>/<slug:event_slug>/',
        views.RegisterBegin.as_view(),
        name="register_event",
    ),

    path(
        '<slug:league_slug>/<slug:event_slug>/create-account',
        views.RegisterCreateAccount.as_view(),
        name="create_account",
    ),

    path(
        '<slug:league_slug>/<slug:event_slug>/signup',
        views.RegisterShowForm.as_view(),
        name="show_form",
    ),

    path(
        '<slug:league_slug>/<slug:event_slug>/done',
        views.RegisterDone.as_view(),
        name="done",
    ),
]
