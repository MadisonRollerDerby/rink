from crispy_forms.helper import FormHelper
from django.forms import ModelForm

from registration.models import RegistrationData


class RegistrationForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = RegistrationData
        exclude = ['invite',]
