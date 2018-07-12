from celery import shared_task

from league.utils import send_email

@shared_task
def test_email(league, to_email):
    send_email(
        league=league,
        to_email=to_email,
        template="test_email",
        context={
        },
    )