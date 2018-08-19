from django import forms
from crispy_forms.helper import FormHelper


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
