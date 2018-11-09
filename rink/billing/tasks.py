from django.utils import timezone

from celery import shared_task

from .models import BillingPeriod, UserStripeCard
from league.utils import send_email
from billing.models import Payment, Invoice, BillingSubscription


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

@shared_task(ignore_result=True)
def email_invoice(invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    subject = "{} - {} Invoice".format(invoice.league.name, invoice.description)

    send_email(
        league=invoice.league,
        to_email=invoice.user.email,
        template="new_invoice",
        context={
            'user': invoice.user,
            'invoice': invoice,
            'subject': subject,
        },
    )

@shared_task(ignore_result=True)
def alert_admin_to_generate_invoices():
    pass


@shared_task(ignore_result=True)
def alert_admin_to_capture_invoices():
    pass


@shared_task(ignore_result=True)
def generate_invoices():
    """
    1) Get all billing periods within the previous 14 days.
        14 days is arbritary, in the event celery/cron breaks and we have to
        catch up. We could track when billing periods are actually scanned for
        new invoices to generate but this method seems easier right now.
    2) Get all active subscriptions tied to this event.
    3) If the subscription was created AFTER the invoice date of the billing period:
        a) Create them an invoice (if it doesn't already exist)
        b) Send them an email notifying them of the new invoice.
    """
    billing_periods = BillingPeriod.objects.filter(
        invoice_date__lte=timezone.now(),
        invoice_date__gt=timezone.now() - timezone.timedelta(days=14)
    )

    for bp in billing_periods:
        subscriptions = BillingSubscription.objects.filter(
            event=bp.event,
            status='active',
        )
        for subscription in subscriptions:
            if subscription.create_date.date() < bp.invoice_date:
                # generate_invoice is a shortcut for create or get this Invoice.
                invoice, created = bp.generate_invoice(subscription, description="Dues")
                if created:
                    email_invoice.delay(invoice.pk)


@shared_task(ignore_result=True)
def capture_invoices():
    invoices = Invoice.objects.filter(
        due_date__lte=timezone.now(),
        status='unpaid',
        autopay_disabled=False,
    )

    for invoice in invoices:
        # Attempt to charge this invoice using the card on file.
        try:
            usc = UserStripeCard.objects.get(league=invoice.league, user=invoice.user)
        except UserStripeCard.DoesNotExist:
            continue

        try:
            payment = usc.charge(invoice=invoice)
        # probably should do more here?
        except ValueError as e:
            print("error: ", e)
        except Exception as e:
            print("error: ", e)
