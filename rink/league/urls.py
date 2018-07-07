from django.urls import path

from . import views

app_name = 'league'
urlpatterns = [
    #path('', views.IndexView.as_view(), name='index'),
    #path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    
    path('<slug:organization_slug>/leagues/', views.LeagueAdminList.as_view(), name="league_list"),
    path('<slug:organization_slug>/league/', views.LeagueAdminCreate.as_view(), name="league_create"),
    path('<slug:organization_slug>/league/<slug:slug>', views.LeagueAdminUpdate.as_view(), name="league_update"),
    path('<slug:organization_slug>/permissions/', views.OrganizationPermissionsView.as_view(), name="organization_permissions"),
    path('<slug:organization_slug>/permission/', views.OrganizationPermissionsChange.as_view(), name="organization_permissions_create"),
    path('<slug:organization_slug>/permission/<int:user_id>', views.OrganizationPermissionsChange.as_view(), name="organization_permissions_update"),
    path('<slug:organization_slug>/create-user/', views.CreateUserView.as_view(), name="create_rink_user"),

]