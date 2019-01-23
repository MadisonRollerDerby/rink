from celery import shared_task

from league.utils import send_email

from voting.models import VotingInvite


@shared_task(ignore_result=True)
def send_voting_invite(invite_ids=[], reminder=False):
    if reminder:
        template = 'voting_reminder'
    else:
        template = 'voting_invite'

    for invite in invite_ids:
        invite = VotingInvite.objects.get(pk=invite)

        send_email(
            league=invite.election.league,
            to_email=invite.user.email,
            template=template,
            context={
                'invite': invite,
                'election': invite.election,
                'user': invite.user,
            },
        )
