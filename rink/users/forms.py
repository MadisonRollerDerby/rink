from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import User


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', 'Submit'))

    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'derby_name',
            'derby_number',
        ]