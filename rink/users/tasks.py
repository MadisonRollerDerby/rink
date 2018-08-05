from celery import shared_task

from league.utils import send_email

from league.models import League

@shared_task(ignore_result=True)
def notify_admin_of_user_changes(league_id, initial, updated):
    league = League.objects.get(pk=league_id)
    if league.email_from_address:
        send_email(
            league=League.objects.get(pk=league_id),
            to_email=league.email_from_address,
            template="users_profile_updated_alert",
            context={
                'initial': initial,
                'updated': updated,
            },
        )

