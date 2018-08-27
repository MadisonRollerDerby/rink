import django_tables2 as tables
from django_tables2.utils import A

from users.models import User


class RosterTable(tables.Table):
    full_name = tables.Column(order_by=('first_name', 'last_name'))
    derby_name = tables.Column()
    email = tables.Column()
    edit = tables.LinkColumn(
        'roster:admin_profile',
        text=lambda record: "View User", kwargs={
            'pk': A('pk'),
        })

    class Meta:
        model = User
        fields = ['full_name', 'derby_name', 'email', 'edit']
