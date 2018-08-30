import django_tables2 as tables
from django_tables2.utils import A

from users.models import User


class RosterTable(tables.Table):
    legal_name = tables.Column(accessor='legal_name', order_by=('first_name', 'last_name'))
    derby_name = tables.Column()
    email = tables.Column()

    class Meta:
        model = User
        fields = ['legal_name', 'derby_name', 'email']
        row_attrs = {
            'data-id': lambda record: record.pk
        }
