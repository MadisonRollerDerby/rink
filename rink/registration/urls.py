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
]