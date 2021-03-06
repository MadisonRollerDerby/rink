from celery import shared_task
from django.utils import timezone

from billing.models import Payment
from league.utils import send_email
from registration.models import RegistrationInvite, RegistrationData

from markdownx.utils import markdownify


@shared_task
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


@shared_task
def send_registration_confirmation(registration_data_id, payment_data_id=None):
    #try:
    registration_data = RegistrationData.objects.get(pk=registration_data_id)
    payment_data = None
    if payment_data_id:
        payment_data = Payment.objects.get(pk=payment_data_id)
    #except RegistrationData.DoesNotExist:
    #    raise RegistrationData.DoesNotExist
    
    send_email(
        league=registration_data.event.league,
        to_email=registration_data.user.email,
        template="registration_confirmation",
        context={
            'user': registration_data.user,
            'event': registration_data.event,
            'registration': registration_data,
            'payment': payment_data,
        },
    )
    return True


@shared_task
def send_registration_invite_reminder(event_id, invite_ids=[], custom_message=''):
    for invite_id in invite_ids:
        try:
            invite = RegistrationInvite.objects.get(pk=invite_id, event__pk=event_id)
        except RegistrationInvite.DoesNotExist:
            continue

        reminder_subject = "*REMINDER* "
        custom_message_html = markdownify(custom_message)
        send_email(
            league=invite.event.league,
            to_email=invite.email,
            template="registration_invite",
            context={
                'invite': invite,
                'reminder_subject': reminder_subject,
                'custom_message': custom_message_html,
            },
        )
