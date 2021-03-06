from django.urls import path

from . import views

app_name = 'legal'
urlpatterns = [
    #path('', views.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views.DetailView.as_view(), name='detail'),

    # Leage Admin Views
    path('admin/documents/', 
        views.LegalDocumentList.as_view(),
        name="admin_document_list"),

    path('admin/document/', 
        views.LegalDocumentCreateUpdate.as_view(),
        name="admin_document_create_update"),

    path('admin/document/<int:document_id>/', 
        views.LegalDocumentCreateUpdate.as_view(),
        name="admin_document_create_update"),

    path('admin/document/<int:document_id>/delete', 
        views.LegalDocumentDelete.as_view(),
        name="admin_document_delete"),


    # User Views
    path('signed-forms/', 
        views.UserLegalSignaturesListView.as_view(),
        name="signed_forms"),


    # Public Views
    path('<slug:league_slug>/<slug:document_slug>/',
        views.LegalDocumentPublicView.as_view(),
        name="view_legal_document"),

    path('<slug:league_slug>/event/<slug:event_slug>/',
        views.LegalDocumentEventView.as_view(),
        name="view_event_legal_documents"),
]