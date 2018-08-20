import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from .models import Invoice


class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        fields = ['id', 'user', 'status', 'invoice_amount', 'invoice_date', 'due_date', 'payment_date']

    def render_id(self, value):
        return format_html("<a href='{}'>#{}</a>",
            reverse('billing:billing_admin_detail', kwargs={'pk': value}),
            value
        )

    def render_invoice_amount(self, value):
        return '${}'.format(value)