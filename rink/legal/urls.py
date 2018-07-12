from django.urls import path

from . import views

app_name = 'legal'
urlpatterns = [
    #path('', views.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views.DetailView.as_view(), name='detail'),

    # Public Views
    path('<slug:league_slug>/<slug:document_slug>/', 
        views.LegalDocumentPublicView.as_view(),
        name="view_legal_document"),
]