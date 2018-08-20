from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper

from .models import PAYMENT_PROCESSOR_CHOICES, Invoice


class UpdateStripeCardForm(forms.Form):
    stripe_token = forms.CharField(max_length=50)


class PayNowForm(forms.Form):
    invoice_id = forms.IntegerField()


class InvoiceFilterForm(forms.Form):
    # For Invoice Admin filtering form
    search = forms.CharField(max_length=200, label='', required=False)
    paid = forms.BooleanField(initial=True, required=False)
    unpaid = forms.BooleanField(initial=True, required=False)
    refunded = forms.BooleanField(initial=True, required=False)
    canceled = forms.BooleanField(initial=True, required=False)
    filtered = forms.BooleanField(initial=True, required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.fields['search'].widget.attrs.update({'placeholder': "Search #, Name, Email"})


class QuickPaymentForm(forms.Form):
    processor = forms.ChoiceField(choices=PAYMENT_PROCESSOR_CHOICES, required=True, initial='cash')
    amount = forms.DecimalField(min_value=0.00, decimal_places=2)
    transaction_id = forms.CharField(max_length=200, required=False)
    payment_date = forms.DateField(initial=timezone.now())


class QuickInvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['invoice_amount', 'description', 'status', 'invoice_date', 'due_date']


class QuickRefundForm(forms.Form):
    refund_amount = forms.DecimalField(min_value=0.00, decimal_places=2)
    refund_reason = forms.CharField(max_length=200, required=False)