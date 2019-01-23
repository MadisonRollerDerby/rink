from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, ButtonHolder


class ElectionEmailInviteForm(forms.Form):
    emails = forms.CharField(
        widget=forms.Textarea,
        label="Email Addresses",
        help_text="Email addresses invites should be sent to. One per line, please. Email addresses must match user account on file.",
        required=True,
    )

    def __init__(self, league, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            'emails',
            'billing_group',
            ButtonHolder(
                Submit('submit', 'Send Invites to Vote', css_class='button white')
            )
        )

    class Meta:
        fields = ['emails', ]
