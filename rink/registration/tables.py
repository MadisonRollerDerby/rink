import django_tables2 as tables
from django_tables2.utils import A

import django_filters

from registration.models import Roster


class RosterFilter(django_filters.FilterSet):
    class Meta:
        model = Roster
        fields = ['email', 'first_name', 'last_name']


class RosterTable(tables.Table):
    full_name = tables.Column(order_by=('first_name', 'last_name'))
    derby_name = tables.Column()
    edit = tables.LinkColumn(
        'registration:event_admin_roster_detail',
        text=lambda record: "Edit", kwargs={
            'event_slug': A('event.slug'),
            'roster_id': A('pk'),
        })

    class Meta:
        model = Roster
        fields = ['full_name', 'derby_name', 'edit']
