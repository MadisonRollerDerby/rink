import django_tables2 as tables
from django_tables2.utils import A

from registration.models import Roster


class RosterTable(tables.Table):
    legal_name = tables.Column(accessor='legal_name', order_by=('last_name', 'first_name'))
    derby_name = tables.Column()
    edit = tables.LinkColumn(
        'registration:event_admin_roster_detail',
        text=lambda record: "Edit", kwargs={
            'event_slug': A('event.slug'),
            'roster_id': A('pk'),
        })

    class Meta:
        model = Roster
        fields = ['legal_name', 'derby_name', 'edit']
