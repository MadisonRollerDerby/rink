from django.utils import timezone

# from django import forms
# from django.utils import timezone


#class DateDropdownSelectorForm(object):
"""
day = forms.ChoiceField(widget=forms.Select(), choices=self.get_date_months(), required=True)
month = forms.ChoiceField(widget=forms.Select(), choices=self.get_month_months(), required=True)
year = forms.ChoiceField(widget=forms.Select(), choices=self.get_year_months(), required=True)

def clean(self):
    cleaned_data = super().clean()

    try:
        timezone.datetime(cleaned_data.get('year'), cleaned_data.get('month'), cleaned_data.get('day'))
    except ValueError:
        raise forms.ValidationError("Date does not appear to be valid")

"""


def get_date_months():
    return (
        ('', 'Month'),
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December'),
    )


def get_date_days():
    return [('', 'Day')] + [(str(x), x) for x in range(1, 32)]


def get_date_years(back_num_years=90):
    return [('', 'Year')] + [(str(x), x) for x in
        reversed(range(timezone.now().year - back_num_years, timezone.now().year))]
