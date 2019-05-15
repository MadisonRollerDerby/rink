from django.db import models
from django.core.validators import MinValueValidator

from markdownx.utils import markdownify

from decimal import Decimal


class TicketEvent(models.Model):
    league = models.ForeignKey(
        "league.League",
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        "Event Name",
        max_length=100,
        help_text="Example: 'Wrecker Social 2019 Super Fun TIME!",
    )

    slug = models.SlugField(
        "Event Slug",
        max_length=100,
        help_text="URL to the event ticket registration thing. Example: 'wrecker-social-2019-okay-great' "
    )

    description = models.TextField(
        "Event Description",
        help_text="Blurb of text shown in the description. You can use <a target='_blank' href='https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet'>Markdown Code</a> to format the document.",
    )

    open_date = models.DateTimeField(
        "Registration Opens On",
        blank=True,
        null=True,
        help_text="The date/time that the registration form becomes available. If you set it to blank, registration is open now.",
    )

    closes_date = models.DateTimeField(
        "Registration Closes On",
        blank=True,
        null=True,
        help_text="The date/time that the registration form becomes available. If you set it to blank, registration will never close.",
    )

    logo = models.ImageField(upload_to='tickets', blank=True, null=True)

    price = models.DecimalField(
        "Amount Paid",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price of event to charge for a ticket.",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    def __str__(self):
        return "{} - {}".format(self.league.name, self.name)

    @property
    def description_html(self):
        return markdownify(self.description)


class TicketPurchase(models.Model):
    event = models.ForeignKey(
        "tickets.TicketEvent",
        on_delete=models.CASCADE,
    )
    
    real_name = models.CharField(
        "Real Name",
        max_length=100,
    )

    derby_name = models.CharField(
        "Derby Name",
        max_length=100,
        blank=True,
    )

    email = models.EmailField(
        "Ticket Email",
        max_length=100,
    )

    transaction_id = models.CharField(
        "Transaction ID",
        max_length=100,
        blank=True,
    )

    amount = models.DecimalField(
        "Amount Paid",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount paid for this transaction",
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    payment_date = models.DateTimeField(
        "Date Paid",
        auto_now_add=True,
    )

    def __str__(self):
        return "{} - {} - {}".format(self.event.name, self.name, self.payment_date)
