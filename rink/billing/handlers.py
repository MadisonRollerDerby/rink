from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Invoice, Payment, UserStripeCard
from users.models import UserLog


@receiver(post_save, sender=Invoice)
def user_log_invoice_created(sender, instance, created, **kwargs):
    if created:
        UserLog.objects.create(
            user=instance.user,
            league=instance.league,
            message="Invoice #{} created for *{}* with amount ${}.".format(
                instance.pk, instance.description, instance.invoice_amount
            ),
            group="billing",
            content_object=instance,
        )


@receiver(post_save, sender=Payment)
def user_log_payment_created(sender, instance, created, **kwargs):
    if created:
        UserLog.objects.create(
            user=instance.user,
            league=instance.league,
            message="Payment received: {}".format(instance),
            group="billing",
            content_object=instance,
        )


@receiver(post_save, sender=UserStripeCard)
def user_log_payment_created(sender, instance, created, **kwargs):
    UserLog.objects.create(
        user=instance.user,
        league=instance.league,
        message="Credit Card updated: {}".format(instance),
        group="billing",
        content_object=instance,
    )
