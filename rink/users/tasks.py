from celery import shared_task

from league.utils import send_email


@shared_task(ignore_result=True)
def notify_admin_of_user_changes(league, initial, updated):
    send_email(
        league=league,
        to_email="test@test.com", #league.email_from_address,
        template="users_profile_updated_alert",
        context={
            'initial': initial,
            'updated': updated,
        },
    )