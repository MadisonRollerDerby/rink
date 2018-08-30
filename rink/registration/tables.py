import django_tables2 as tables
from django_tables2.utils import A

from registration.models import Roster


class RosterTable(tables.Table):
    legal_name = tables.Column(accessor='full_name', order_by=('last_name', 'first_name'))
    derby_name = tables.Column()

    class Meta:
        model = Roster
        fields = ['full_name', 'derby_name']
        row_attrs = {
            'data-id': lambda record: record.pk
        }
