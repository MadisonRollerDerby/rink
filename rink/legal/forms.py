from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import LegalDocument


class LegalDocumentAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super(LegalDocumentAdminForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', 'Submit'))

    class Meta:
        model = LegalDocument
        fields = [
            'name',
            'date',
            'content',
        ]
        widgets = {
            'date': forms.TextInput(attrs={'type':'date'}),
        }