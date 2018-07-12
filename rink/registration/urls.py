from django.urls import path

from . import views

app_name = 'registration'
urlpatterns = [
    #path('', views_admin.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views_admin.DetailView.as_view(), name='detail'),
    
    path(
        '<slug:event_slug>/<uuid:invite_key>/', 
        views.RegistrationBegin.as_view(), 
        name="register_event_uuid",
    ),

    path(
        '<slug:event_slug>/', 
        views.RegistrationBegin.as_view(),
        name="register_event",
    ),
]