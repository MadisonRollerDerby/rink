from django.urls import path

from voting import views as voting_views
from voting import views_admin as voting_admin_views


app_name = 'voting'
urlpatterns = [
    # Public vote view
    path(
        '<slug:league_slug>/<uuid:vote_key>',
        voting_views.ViewBallot.as_view(),
        name="view_voting_invite",
    ),

    path(
        '<slug:league_slug>/<slug:election_slug>/thanks',
        voting_views.BallotThanks.as_view(),
        name="view_voting_thanks",
    ),

    # Voting stats and admin stuff, invites, etc.
    path(
        'admin',
        voting_admin_views.AdminVotingElectionsList.as_view(),
        name="admin_voting",
    ),
    path(
        'admin/<slug:election_slug>',
        voting_admin_views.AdminVotingStats.as_view(),
        name="admin_voting_stats_details",
    ),
    path(
        'admin/invite/<slug:election_slug>',
        voting_admin_views.AdminVotingInvites.as_view(),
        name="admin_voting_invites",
    ),

]
