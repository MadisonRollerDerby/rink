from django import forms


class TicketForm(forms.Form):
    real_name = forms.CharField(max_length=100, required=True)
    derby_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    stripe_token = forms.CharField(max_length=50, required=True)
