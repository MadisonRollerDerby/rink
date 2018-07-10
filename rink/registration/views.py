from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View

from billing.models import BillingPeriod
from league.mixins import LeagueAdminRequiredMixIn
from league.models import Organization, League
from registration.forms import RegistrationForm, RegistrationAdminEventForm, \
    BillingPeriodInlineForm
from registration.models import RegistrationEvent


class RegistrationBegin(View):
    def get(self, request, registration_slug, invite_key=None):
        #return HttpResponse("{}, {}".format(registration_slug, invite_key))

        registration_form = RegistrationForm

        return render(request, 'registration/registration.html', {
                'registration_form': registration_form
            }
        )




# Base class for permission checking and views here.
# saves org, league and event.
# Does some magic for making it easier to render the UI
class EventAdminBaseView(LeagueAdminRequiredMixIn, View):
    event_menu_selected = None

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=request.session['view_organization'])
        self.league = get_object_or_404(League, pk=request.session['view_league'])
        try:
            self.event = get_object_or_404(RegistrationEvent, slug=kwargs['event_slug'])
            self.event_slug = self.event.slug
        except KeyError:
            self.event = None
            self.event_slug = None

        return super(EventAdminBaseView, self).dispatch(request, *args, **kwargs)

    def get_context(self):
        return {
            'organization_slug': self.organization.slug,
            'league_slug': self.league.slug,
            'event': self.event,
            'event_slug': self.event_slug,
            'event_menu_selected': self.event_menu_selected,
        }
    def render(self, request, context={}):
        return render(request, self.template, {**context, **self.get_context()})


# List of registration events
class EventAdminList(EventAdminBaseView):
    template = 'registration/event_admin_list.html'

    def get(self, request, *args, **kwargs):
        events = RegistrationEvent.objects.filter(league=self.league)

        current_events = events.filter(end_date__gte=timezone.now())
        past_events = events.filter(end_date__lt=timezone.now())

        return self.render(request, {
            'current_events': current_events,
            'past_events': past_events,
        })


# Create a new registration event
class EventAdminCreate(EventAdminBaseView):
    template = 'registration/event_admin_create.html'

    def get(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm()
        
        return self.render(request, {
            'form': form,
        })

    def post(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.league = self.league
            event.save()

            auto_create = form.cleaned_data['automatic_billing_dates']

            if auto_create == "monthly":
                billing_period = event.create_monthly_biling_periods()
            elif auto_create == "once":
                billing_periods = event.create_billing_period()

            return HttpResponseRedirect(
                reverse("registration:event_admin_invites", 
                    kwargs={
                    'organization_slug':organization_slug, 
                    'league_slug':league_slug, 
                    'event_slug':event.slug,
            }))

        return self.render(request, {
            'form': form,
        })


class EventAdminSettings(EventAdminBaseView):
    template = 'registration/event_admin_settings.html'
    event_menu_selected = "settings"

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'event_form':  RegistrationAdminEventForm(instance=self.event),
        })


class EventAdminRoster(EventAdminBaseView):
    template = 'registration/event_admin_roster.html'
    event_menu_selected = "roster"

    def get(self, request, *args, **kwargs):
        return self.render(request, {})

    def post(self, request, *args, **kwargs):
        pass


class EventAdminInvites(EventAdminBaseView):
    template = 'registration/event_admin_invites.html'
    event_menu_selected = "invites"

    def get(self, request, *args, **kwargs):
        return self.render(request, {})

    def post(self, request, *args, **kwargs):
        pass


class EventAdminBillingPeriods(EventAdminBaseView):
    template = 'registration/event_admin_billing_periods.html'
    event_menu_selected = "billingperiods"

    def get(self, request, *args, **kwargs):
        return self.render(request, {})

    def post(self, request, *args, **kwargs):
        pass

