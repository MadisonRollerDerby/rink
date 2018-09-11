import django_tables2 as tables
from django_tables2.utils import A

from registration.models import Roster, RegistrationInvite


class RosterTable(tables.Table):
    legal_name = tables.Column(accessor='full_name', order_by=('last_name', 'first_name'))
    derby_name = tables.Column()

    class Meta:
        model = Roster
        fields = ['full_name', 'derby_name']
        row_attrs = {
            'data-id': lambda record: record.pk
        }


class ReminderTable(tables.Table):
    checkbox = tables.CheckBoxColumn(accessor="pk")
    email = tables.Column(accessor='email')
    username = tables.Column(accessor='user')

    class Meta:
        model = RegistrationInvite
        fields = ['checkbox', 'email', 'username']
