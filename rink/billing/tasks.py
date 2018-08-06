from celery import shared_task

from league.utils import send_email
from billing.models import Payment, Invoice


@shared_task(ignore_result=True)
def email_payment_receipt(payment_id):
    payment = Payment.objects.get(pk=payment_id)
    invoices = Invoice.objects.filter(payment=payment)

    if invoices.count() == 1:
        subject = "{} {} Payment Receipt #{}".format(
            payment.league.name, invoices[0].description, payment.id)
    else:
        subject = "{} Payment Receipt #{}".format(
            payment.league.name, payment.id)

    send_email(
        league=payment.league,
        to_email=payment.user.email,
        template="payment_receipt",
        context={
            'user': payment.user,
            'invoices': invoices,
            'payment': payment,
            'subject': subject,
        },
    )
