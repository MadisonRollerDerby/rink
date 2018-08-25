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

    # League view switcher
    path('switch-leagues-view/<slug:league_slug>', views.SwitchLeagueView.as_view(), name="switch_league_view"),

    # Insurance Types Admin
    path('<slug:organization_slug>/league/<slug:slug>/insurance',
        views.LeagueInsuranceTypesListView.as_view(),
        name="insurance_list"),

    path('<slug:organization_slug>/league/<slug:slug>/insurance/<int:insurance_type_id>',
        views.LeagueInsuranceTypesChangeView.as_view(),
        name="insurance_change"),

    path('<slug:organization_slug>/league/<slug:slug>/insurance/new',
        views.LeagueInsuranceTypesCreateView.as_view(),
        name="insurance_create"),


    # Billing Groups Admin
    path('<slug:organization_slug>/league/<slug:slug>/billing-groups',
        views.LeagueBillingGroupsListView.as_view(),
        name="billing_groups_list"),

    path('<slug:organization_slug>/league/<slug:slug>/billing-groups/<int:billing_group_id>',
        views.LeagueBillingGroupsChangeView.as_view(),
        name="billing_groups_change"),

    path('<slug:organization_slug>/league/<slug:slug>/billing-groups/new',
        views.LeagueBillingGroupsCreateView.as_view(),
        name="billing_groups_create"),
]