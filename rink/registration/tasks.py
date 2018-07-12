from celery import shared_task
from django.utils import timezone

from league.utils import send_email
from registration.models import RegistrationInvite


@shared_task(ignore_result=True)
def send_registration_invite_email(invite_ids=[]):
    for invite_id in invite_ids:
        try:
            invite = RegistrationInvite.objects.get(pk=invite_id)
        except RegistrationInvite.DoesNotExist:
            continue

        # Don't send invites if they have completed registration
        # or the sent date is set (already sent invite).
        # To resend an invite, we need to set sent_date to null
        # before calling this task.
        if invite.completed_date or invite.sent_date:
            continue

        send_email(
            league=invite.event.league,
            to_email=invite.email,
            template="registration_invite",
            context={
                'invite': invite,
            },
        )

        invite.sent_date = timezone.now()
        invite.save()