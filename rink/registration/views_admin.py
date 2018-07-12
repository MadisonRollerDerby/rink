from django.contrib import messages 
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View

from guardian.shortcuts import get_users_with_perms
import re

from billing.models import BillingPeriod
from league.mixins import LeagueAdminRequiredMixIn
from league.models import Organization, League
from .forms_admin import RegistrationAdminEventForm, BillingPeriodInlineForm, \
    EventInviteEmailForm, EventInviteAjaxForm
from .models import RegistrationEvent, RegistrationInvite
from users.models import User

from registration.tasks import send_registration_invite_email


# Base class for permission checking and views here.
# saves org, league and event.
# Does some magic for making it easier to render the UI
class EventAdminBaseView(LeagueAdminRequiredMixIn, View):
    event = None
    event_slug = None
    event_menu_selected = None
    invites_menu_selected = None

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=request.session['view_organization'])
        self.league = get_object_or_404(League, pk=request.session['view_league'])
        try:
            self.event = get_object_or_404(RegistrationEvent, slug=kwargs['event_slug'])
            self.event_slug = self.event.slug
        except KeyError:
            pass

        return super(EventAdminBaseView, self).dispatch(request, *args, **kwargs)

    def get_context(self):
        return {
            'organization_slug': self.organization.slug,
            'league_slug': self.league.slug,
            'event': self.event,
            'event_slug': self.event_slug,
            'event_menu_selected': self.event_menu_selected,
            'invites_menu_selected': self.invites_menu_selected
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
        form = RegistrationAdminEventForm(event=self.event)
        
        return self.render(request, {
            'form': form,
        })

    def post(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm(request.POST, event=self.event)
        if form.is_valid():
            event = form.save(commit=False)
            event.league = self.league
            event.save()
            form.save_m2m()

            auto_create = form.cleaned_data['automatic_billing_dates']

            if auto_create == "monthly":
                billing_period = event.create_monthly_biling_periods()
            elif auto_create == "once":
                billing_periods = event.create_billing_period()

            return HttpResponseRedirect(
                reverse("registration:event_admin_invites", kwargs={'event_slug':event.slug }))

        return self.render(request, {
            'form': form,
        })


class EventAdminSettings(EventAdminBaseView):
    template = 'registration/event_admin_settings.html'
    event_menu_selected = "settings"

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'event_form':  RegistrationAdminEventForm(event=self.event, instance=self.event),
        })

    def post(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm(event=self.event, data=request.POST)
        if form.is_valid():
            event = form.save()

            return HttpResponseRedirect(
                reverse("registration:event_admin_settings", 
                    kwargs={'event_slug':event.slug })
            )

        return self.render(request, {'event_form': form})


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
    invites_menu_selected = "invites"

    def get(self, request, *args, **kwargs):
        # Get all users who have permissions to access this league.
        # Pre-cache if they have an attached invite to this league.
        invites = RegistrationInvite.objects.filter(event=self.event)

        invites_completed = RegistrationInvite.objects.filter(
            event=self.event,
            completed_date__isnull=False,
        ).count()

        invites_waiting = RegistrationInvite.objects.filter(
            event=self.event,
            completed_date__isnull=True,
        ).count()

        for invite in invites:
            if not invite.sent_date:
                invite.row_class = "warning"
                invite.invite_status = "Queued"
            elif not invite.completed_date:
                invite.row_class = "info"
                invite.invite_status = "Invited"
            elif invite.public_registration:
                invite.row_class = "success"
                invite.invite_text = "Registered via Public Link"
                invite.invite_status = "Completed"
            else:
                invite.row_class = "success"
                invite.invite_text = "Registered via Invite"
                invite.invite_status = "Completed"

        return self.render(request, {
            'invites': invites,
            'invites_completed': invites_completed,
            'invites_waiting': invites_waiting,
            'event_admin_template_include': 'registration/event_admin_invites_list.html',
        })

    def post(self, request, *args, **kwargs):
        # This method only handles the invite-<event ID> and user-<user ID>
        # values sent from AJAX requests.
        form = EventInviteAjaxForm(request.POST)
        if form.is_valid():
            regex = re.compile('^(invite|user)-(\d+)$')
            match = regex.match(form.cleaned_data['user_or_invite_id'])
            invite_class = match.group(1)
            invite_or_user_id = match.group(2)

            if invite_class == "user":
                # Check for existing invite to this user
                user = get_object_or_404(User, pk=invite_or_user_id)
                try:
                    existing_invite = RegistrationInvite.objects.get(user=user, event=self.event)
                except RegistrationInvite.DoesNotExist:
                    existing_invite = None

                if existing_invite:
                    # we are resending
                    if existing_invite.completed_date:
                        # already registered? huh. probably should never be here.
                        # this is probably the wrong error to send too.
                        raise HttpResponse(status=500)

                    invite = existing_invite
                    invite.sent_date = None
                    invite.save()
                else:
                    invite = RegistrationInvite.objects.create(
                        user=user,
                        email=user.email,
                        event=self.event,
                    )

            elif invite_class == "invite":
                invite = get_object_or_404(RegistrationInvite, pk=invite_or_user_id, event=self.event)
                if invite.completed_date:
                    # already registered? huh. probably should never be here.
                    # this is probably the wrong error to send too.
                    raise HttpResponse(status=500)

                invite.sent_date = None
                invite.save()

            send_registration_invite_email.delay(invite_ids=[invite.pk])
            return HttpResponse("OK")

        raise HttpResponse(status=500)


class EventAdminInviteEmails(EventAdminBaseView):
    template = 'registration/event_admin_invites.html'
    event_menu_selected = "invites"
    invites_menu_selected = "emails"

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'form': EventInviteEmailForm(),
            'event_admin_template_include': 'registration/event_admin_invites_emails.html',
        })

    def post(self, request, *args, **kwargs):
        form = EventInviteEmailForm(request.POST)
        if form.is_valid():
            error = False
            emails = form.cleaned_data['emails'].splitlines()
            for email in emails:
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(request, "Invalid email: {}. Please check your list and try again.".format(email))
                    error = True

            if not error:
                invite_ids = []
                for email in emails:

                    try:
                        existing_invite = RegistrationInvite.objects.get(email=email, event=self.event)
                    except RegistrationInvite.DoesNotExist:
                        existing_invite = None

                    # If invite already exists for this email, just resend it
                    # and go onto the next email address.
                    if existing_invite:
                        invite_ids.append(existing_invite.pk)
                        continue

                    invite = RegistrationInvite.objects.create(
                        email=email,
                        event=self.event
                    )

                    # Attempt to match existing user to the email address
                    try:
                        invite.user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        pass
                    else:
                        invite.save()

                    invite_ids.append(invite.pk)

                send_registration_invite_email.delay(invite_ids=invite_ids)

                messages.success(request, 'Sending {} invites. They will be delivered shortly.'.format(len(emails)))
                return HttpResponseRedirect(
                    reverse("registration:event_admin_invite_emails", kwargs={'event_slug':self.event.slug }))

        return self.render(request, {
            'form': EventInviteEmailForm(),
            'event_admin_template_include': 'registration/event_admin_invites_emails.html',
        })




class EventAdminInviteUsers(EventAdminBaseView):
    template = 'registration/event_admin_invites.html'
    event_menu_selected = "invites"
    invites_menu_selected = "users"

    def get(self, request, *args, **kwargs):
        # Get all users who have permissions to access this league.
        # Pre-cache if they have an attached invite to this league.
        league_users = get_users_with_perms(self.league).prefetch_related(
            Prefetch('registrationinvite_set',
            queryset=RegistrationInvite.objects.filter(event__slug='test-event'),
                to_attr='cached_invites'
            )
        )

        for user in league_users:
            user.row_class = ""
            user.invite_status = "Not Invited"
            if user.cached_invites:
                try:
                    invite = user.cached_invites[0]
                except RegistrationInvite.DoesNotExist:
                    continue

                if not invite.sent_date:
                    user.row_class = "warning"
                    user.invite_status = "Queued"
                elif not invite.completed_date:
                    user.row_class = "info"
                    user.invite_status = "Invited"
                elif invite.public_registration:
                    user.row_class = "success"
                    user.invite_text = "Registered via Public Link"
                    user.invite_status = "Completed"
                else:
                    user.row_class = "success"
                    user.invite_text = "Registered via Invite"
                    user.invite_status = "Completed"

        return self.render(request, {
            'users': league_users,
            'event_admin_template_include': 'registration/event_admin_invites_users.html',
        })

    def post(self, request, *args, **kwargs):

        pass


class EventAdminBillingPeriods(EventAdminBaseView):
    template = 'registration/event_admin_billing_periods.html'
    event_menu_selected = "billingperiods"

    def get(self, request, *args, **kwargs):
        return self.render(request, {})

    def post(self, request, *args, **kwargs):
        pass

