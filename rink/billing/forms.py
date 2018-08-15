from django import forms


class UpdateStripeCardForm(forms.Form):
    stripe_token = forms.CharField(max_length=50)


class PayNowForm(forms.Form):
    invoice_id = forms.IntegerField()