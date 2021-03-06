from django.contrib import messages
from django.core.validators import validate_email
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from django_tables2 import SingleTableView
from django_filters.views import FilterView

import csv
import os
from decimal import Decimal, InvalidOperation
from datetime import datetime
from guardian.shortcuts import get_users_with_perms
import re
from time import gmtime, strftime

from .forms import RegistrationDataForm
from .forms_admin import (RegistrationAdminEventForm, BillingPeriodInlineForm,
    EventInviteEmailForm, EventInviteAjaxForm, EventInviteReminderForm,
    EventInviteDeleteForm)
from .models import RegistrationEvent, RegistrationInvite, Roster
from .resources import RosterResource
from .tables import RosterTable, ReminderTable
from billing.models import (
    BillingPeriod, BillingGroup, BillingPeriodCustomPaymentAmount, Invoice,
    BillingSubscription, UserStripeCard)
from league.mixins import RinkLeagueAdminPermissionRequired
from league.models import Organization, League
from legal.models import LegalSignature
from registration.models import RegistrationData
from users.models import User

from registration.tasks import send_registration_invite_email, send_registration_invite_reminder


# Base class for permission checking and views here.
# saves org, league and event.
# Does some magic for making it easier to render the UI
class EventAdminBaseView(RinkLeagueAdminPermissionRequired, View):
    event = None
    event_slug = None
    event_menu_selected = None
    invites_menu_selected = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.event = get_object_or_404(RegistrationEvent, slug=kwargs['event_slug'])
            self.event_slug = self.event.slug
        except KeyError:
            pass

        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_context(self):
        roster_count = Roster.objects.filter(event=self.event).count()

        pending_invites_count = RegistrationInvite.objects.filter(
            event=self.event,
            completed_date__isnull=True,
        ).count()

        return {
            'organization_slug': self.organization.slug,
            'league_slug': self.league.slug,
            'event': self.event,
            'event_slug': self.event_slug,
            'event_menu_selected': self.event_menu_selected,
            'invites_menu_selected': self.invites_menu_selected,
            'roster_menu_count': roster_count,
            'invites_pending_menu_count': pending_invites_count,
            'csrftoken': get_token(self.request)
        }

    def render(self, request, context={}):
        return render(request, self.template, {**context, **self.get_context()})


class EventAdminTableView(RinkLeagueAdminPermissionRequired, SingleTableView, FilterView):
    event = None
    event_slug = None
    event_menu_selected = None
    invites_menu_selected = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.event = get_object_or_404(RegistrationEvent, slug=kwargs['event_slug'])
            self.event_slug = self.event.slug
        except KeyError:
            pass

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        roster_count = Roster.objects.filter(event=self.event).count()

        pending_invites_count = RegistrationInvite.objects.filter(
            event=self.event,
            completed_date__isnull=True,
        ).count()

        additional_context = {
            'organization_slug': self.organization.slug,
            'league_slug': self.league.slug,
            'event': self.event,
            'event_slug': self.event_slug,
            'event_menu_selected': self.event_menu_selected,
            'invites_menu_selected': self.invites_menu_selected,
            'roster_menu_count': roster_count,
            'invites_pending_menu_count': pending_invites_count,
        }

        return {**context, **additional_context}


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

        form = RegistrationAdminEventForm(league=self.league)

        return self.render(request, {
            'form': form,
        })

    def post(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm(data=request.POST, league=self.league)
        if form.is_valid():
            event = form.save(commit=False)
            event.league = self.league
            event.save()
            form.save_m2m()

            auto_create = form.cleaned_data['automatic_billing_dates']

            if auto_create == "monthly":
                billing_periods = event.create_monthly_billing_periods()
            elif auto_create == "once":
                billing_periods = [event.create_billing_period()]
            else:
                billing_periods = []

            if billing_periods:
                for group in BillingGroup.objects.filter(league=self.league):
                    try:
                        amount = form.cleaned_data['billinggroup{}'.format(group.pk)]
                    except KeyError:
                        continue

                    for period in billing_periods:
                        BillingPeriodCustomPaymentAmount.objects.create(
                            invoice_amount=amount,
                            group=group,
                            period=period,
                        )

            return HttpResponseRedirect(
                reverse("registration:event_admin_invites", kwargs={'event_slug':event.slug }))

        else:
            print(form.errors)

        return self.render(request, {
            'form': form,
        })


class EventAdminSettings(EventAdminBaseView):
    template = 'registration/event_admin_settings.html'
    event_menu_selected = "settings"

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'event_form': RegistrationAdminEventForm(league=self.league, instance=self.event),
        })

    def post(self, request, *args, **kwargs):
        form = RegistrationAdminEventForm(league=self.league, instance=self.event, data=request.POST)
        if form.is_valid():
            event = form.save()

            messages.success(request, 'Saved Event Settings')
            return HttpResponseRedirect(
                reverse("registration:event_admin_settings",
                    kwargs={'event_slug': event.slug})
            )

        return self.render(request, {'event_form': form})


class EventAdminRoster(EventAdminTableView, FilterView):
    template_name = 'registration/event_admin_roster.html'
    event_menu_selected = "roster"
    paginate_by = 50
    table_class = RosterTable
    #filterset_class = RosterFilter

    def get_queryset(self):
        return Roster.objects.filter(event=self.event)


class EventAdminRosterCSV(EventAdminBaseView):
    def get(self, request, *args, **kwargs):
        roster = Roster.objects.filter(event__slug=self.event.slug)
        roster_resource = RosterResource()
        dataset = roster_resource.export(queryset=roster)
        response = HttpResponse(dataset.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=roster={}.csv'.format(self.event.slug)
        return response


class EventAdminMedicalCSV(EventAdminBaseView):
    def get(self, request, *args, **kwargs):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_font('DejaVu','','rink/fonts/DejaVuSansCondensed.ttf',uni=True)

        roster = Roster.objects.filter(event__slug=self.event.slug)

        for roster_entry in roster:

            registration_data = roster_entry.registrationdata_set.first()

            pdf.add_page()
            pdf.set_margins(16, 2)
            pdf.ln(20)

            pdf.set_font('DejaVu','',16)
            pdf.cell(40,40,'Derby Name:')
            pdf.set_font('DejaVu','',48)
            pdf.cell(40,40, roster_entry.user.derby_name)
            pdf.ln(20)
            
            pdf.set_font('DejaVu','',16)
            pdf.cell(40,40,'Real Name:')
            pdf.set_font('DejaVu','',24)
            pdf.cell(40,40, roster_entry.user.first_name + " " + roster_entry.user.last_name)
            pdf.ln(20)
            
            pdf.set_font('DejaVu','',16)
            pdf.cell(60,40,'Date of Birth:')
            pdf.set_font('DejaVu','',24)
            pdf.cell(0,40, str(registration_data.emergency_date_of_birth))
            pdf.ln(10)
            
            pdf.set_font('DejaVu','',16)
            pdf.cell(60,40,'Emergency Contact:')
            pdf.set_font('DejaVu','',24)
            pdf.cell(0,40, registration_data.emergency_contact)
            pdf.ln(10)
            pdf.cell(60,40,'')
            pdf.set_font('DejaVu','',24)
            pdf.cell(0,40, registration_data.emergency_phone)
            pdf.ln(10)
            pdf.cell(60,40,'')
            pdf.set_font('DejaVu','',24)
            pdf.cell(0,40, registration_data.emergency_relationship)
            pdf.ln(15)
            
            if registration_data.emergency_contact_second:
                pdf.set_font('DejaVu','',16)
                pdf.cell(60,40,'Emergency Contact #2:')
                pdf.set_font('DejaVu','',24)
                pdf.cell(0,40, registration_data.emergency_contact_second)
                pdf.ln(10)
                pdf.cell(60,40,'')
                pdf.set_font('DejaVu','',24)
                pdf.cell(0,40, registration_data.emergency_phone_second)
                pdf.ln(10)
                pdf.cell(60,40,'')
                pdf.set_font('DejaVu','',24)
                pdf.cell(0,40, registration_data.emergency_relationship_second)
                pdf.ln(15)

            pdf.set_font('DejaVu','',16)
            pdf.cell(60,40,'Hosptial Preference:')
            pdf.set_font('DejaVu','',24)
            pdf.cell(0,40, registration_data.emergency_hospital)
            pdf.ln(15)
            
            pdf.set_font('DejaVu','',12)
            pdf.multi_cell(0,40,'Medical Conditions:')
            pdf.ln(-15)
            pdf.set_font('DejaVu','',24)
            if registration_data.emergency_allergies == "":
                details = "<none>"
            else:
                details = registration_data.emergency_allergies
            
            pdf.write(12, details)
            pdf.ln(25)

            wftda = ""
            try:
                wftda = int(registration_data.derby_insurance_number)
            except:
                pass

            pdf.set_font('Courier','',7)
            pdf.write(4, 'RINK #' + str(registration_data.user.id) + " | " + str(registration_data.user.email) + " | WFTDA #" + str(wftda) + " | generated on " + strftime("%Y-%m-%d", gmtime()))

        pdf.output('/tmp/rink_medical.pdf', 'F')

        with open('/tmp/rink_medical.pdf', 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = 'inline;filename=rink_medical.pdf'

        os.remove('/tmp/rink_medical.pdf')
        return response


class EventAdminRosterDetail(EventAdminBaseView):
    template = 'registration/event_admin_roster_detail.html'
    event_menu_selected = "roster"

    def get(self, request, roster_id, *args, **kwargs):
        # user
        # roster
        # signup data
        # billing
        #   payments
        #   invoices
        # legal signatures
        roster = get_object_or_404(Roster, event=self.event, pk=roster_id)
        registration_data = RegistrationData.objects.get(roster=roster)
        invoices = Invoice.objects.filter(billing_period__event=self.event)
        invoices_unpaid_count = Invoice.objects.filter(billing_period__event=self.event, status='unpaid').count()
        billing_subscription = BillingSubscription.objects.get(roster=roster)
        billing_periods_future = BillingPeriod.objects.filter(event=self.event, invoice_date__gt=timezone.now())
        signatures = LegalSignature.objects.filter(registration=registration_data)

        update_info_form = RegistrationDataForm(instance=registration_data, event=self.event)

        try:
            card_on_file = UserStripeCard.objects.get(league=self.event.league, user=roster.user)
        except UserStripeCard.DoesNotExist:
            card_on_file = None

        for bpf in billing_periods_future:
            bpf.invoice_amount = bpf.get_invoice_amount(user=roster.user)

        return self.render(request, {
            'user': roster.user,
            'roster': roster,
            'registration_data': registration_data,
            'invoices': invoices,
            'invoices_unpaid_count': invoices_unpaid_count,
            'billing_subscription': billing_subscription,
            'billing_periods_future': billing_periods_future,
            'card_on_file': card_on_file,
            'signatures': signatures,
            'update_info_form': update_info_form,
        })

    def post(self, request, roster_id, *args, **kwargs):
        roster = get_object_or_404(Roster, event=self.event, pk=roster_id)
        registration_data = RegistrationData.objects.get(roster=roster)
        form = RegistrationDataForm(instance=registration_data, data=request.POST)
        form.logged_in_user_id = roster.user.id
        if form.is_valid():
            form.save()
            messages.success(request, "Updated registration details.")

            user = roster.user
            if user.first_name == roster.first_name:
                user.first_name = form.cleaned_data['contact_first_name']
            if user.last_name == roster.last_name:
                user.last_name = form.cleaned_data['contact_last_name']
            if user.email == roster.email:
                user.email = form.cleaned_data['contact_email']
            if user.derby_name == roster.derby_name:
                user.derby_name = form.cleaned_data['derby_name']
            if user.derby_number == roster.derby_number:
                user.derby_number = form.cleaned_data['derby_number']
            user.save()

            # Also update roster entry
            roster.first_name = form.cleaned_data['contact_first_name']
            roster.last_name = form.cleaned_data['contact_last_name']
            roster.derby_name = form.cleaned_data['derby_name']
            roster.derby_number = form.cleaned_data['derby_number']
            roster.email = form.cleaned_data['contact_email']
            roster.save()

            return HttpResponseRedirect(
                reverse("registration:event_admin_roster_detail",
                    kwargs={'event_slug': self.event.slug, 'roster_id': roster.pk }))

        messages.error(request, "Error saving form: {}".format(form.errors))
        return self.get(request, roster_id)


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


class EventAdminInviteDelete(EventAdminBaseView):
    def post(self, request, *args, **kwargs):
        form = EventInviteDeleteForm(request.POST)
        if form.is_valid():
            try:
                invite = RegistrationInvite.objects.get(
                    pk=form.cleaned_data['invite_id'], event=self.event)
            except RegistrationInvite.DoesNotExist:
                raise HttpResponse(status=500)

            invite.delete()
            return HttpResponse("OK")
        
        raise HttpResponse(status=500)


class EventAdminInviteEmails(EventAdminBaseView):
    template = 'registration/event_admin_invites.html'
    event_menu_selected = "invites"
    invites_menu_selected = "emails"

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'form': EventInviteEmailForm(league=self.league),
            'event_admin_template_include': 'registration/event_admin_invites_emails.html',
        })

    def post(self, request, *args, **kwargs):
        form = EventInviteEmailForm(league=self.league, data=request.POST)
        if form.is_valid():
            error = False
            emails = form.cleaned_data['emails'].splitlines()
            billing_group = form.cleaned_data['billing_group']
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
                        event=self.event,
                        billing_group=billing_group,
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
            'form': EventInviteEmailForm(league=self.league),
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
            Prefetch(
                'registrationinvite_set',
                queryset=RegistrationInvite.objects.filter(event=self.event),
                to_attr='cached_invites',
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


class EventAdminInviteReminder(EventAdminBaseView):
    template = 'registration/event_admin_invites.html'
    event_menu_selected = "invites"
    invites_menu_selected = "reminder"


    def get(self, request, *args, **kwargs):
        invites_table = ReminderTable(
            RegistrationInvite.objects.filter(event=self.event, completed_date__isnull=True))
        form = EventInviteReminderForm()
        return self.render(request, {
            'invites_table': invites_table,
            'form': form,
            'event_admin_template_include': 'registration/event_admin_reminder.html',
        })

    def post(self, request, *args, **kwargs):
        form = EventInviteReminderForm(request.POST)
        invite_ids = request.POST.getlist('checkbox')
        if form.is_valid():
            send_registration_invite_reminder.delay(
                event_id=self.event.pk,
                invite_ids=invite_ids,
                custom_message=form.cleaned_data['custom_message'],
            )
        messages.success(request, "Sending {} invite reminder emails.".format(len(invite_ids)))
        return redirect('registration:event_admin_invite_reminder', event_slug=self.event.slug)


class EventAdminBillingPeriods(EventAdminBaseView):
    template = 'registration/event_admin_billing_periods.html'
    event_menu_selected = "billingperiods"

    def get(self, request, *args, **kwargs):
        # Validate that we have already all the entries for the group/periods table
        # This all is pretty sloppy
        periods = BillingPeriod.objects.filter(event=self.event).prefetch_related('billingperiodcustompaymentamount_set')
        groups = BillingGroup.objects.filter(league=self.league)

        group_ids = []
        for group in groups:
            group_ids.append(group.pk)

        updated = False
        for period in periods:
            # Check for groups that do not exist, but SHOULD exist.
            not_existing_groups = group_ids
            for bpcpa in period.billingperiodcustompaymentamount_set.prefetch_related('group').all():
                if bpcpa.group.pk in not_existing_groups:
                    not_existing_groups.remove(bpcpa.group.pk)

            for group_id in not_existing_groups:
                BillingPeriodCustomPaymentAmount.objects.create(
                    group=BillingGroup.objects.get(pk=group_id),
                    period=period,
                    invoice_amount=0
                )
                updated = True

        if updated:
            # let's just repeat ourselves again, eh?
            periods = BillingPeriod.objects.filter(event=self.event).prefetch_related('billingperiodcustompaymentamount_set')

        return self.render(request, {
            'billing_groups': groups,
            'billing_periods': periods,
        })

    def post(self, request, *args, **kwargs):
        """
        Expected data submitted from the form:

        1) New billing periods have field names ending in a matching number.
            - '<field>_new(\d+)' for BillingPeriod fields
            - 'invoice_amount_group(<pk of group>)_new(\d+)'

        2) Existing billing periods have field names formatted as:
            - '<field>(<pk of BillingPeriod>)' for BillingPeriod fields
            - 'invoice_amount_group(<pk of group>)_(<pk of BillingPeriod>)'
            - NOTE: You can change the due_date of all associated invoices by updating the date here.

        3) Deleted billing periods show up as hidden inputs:
            - 'delete(<pk of BillingPeriod>)'
            - NOTE: You cannot delete any billing periods with invoices already generated
        """
        new_regex = re.compile('^name_new(\d+)$')
        existing_regex = re.compile('^name(\d+)$')
        delete_regex = re.compile('^delete(\d+)$')

        billing_groups = BillingGroup.objects.filter(league=self.league)

        error_messages = []
        alert_messages = []
        new_periods = []
        updated_periods = []
        deleted_periods = []

        post = request.POST
        for key, value in post.items():

            new_match = new_regex.match(key)
            existing_match = existing_regex.match(key)
            delete_match = delete_regex.match(key)

            print("{} {}".format(key, new_match))
            if new_match:
                # Add a NEW billing period
                bp_id = '_new{}'.format(new_match.group(1))

                bp = BillingPeriod()
                bp.event = self.event
                bp.league = self.league
                try:
                    bp.name = post['name{}'.format(bp_id)]
                    if bp.name == "":  # Ignore anything with a blank name.
                        continue
                    bp.start_date = datetime.strptime(
                        post['start_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                    bp.end_date = datetime.strptime(
                        post['end_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                    bp.invoice_date = datetime.strptime(
                        post['invoice_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                    bp.due_date = datetime.strptime(
                        post['due_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                except KeyError as e:
                    alert_messages.append("Field not found for NEW billing period. Error: {}".format(str(e)))
                    continue
                except ValueError as e:
                    error_messages.append("Invalid date specified for new due date for '{}'. Error: {}".format(bp.name, str(e)))

                try:
                    bp.full_clean()
                except ValidationError as e:
                    error_messages.append("Invalid data in new row. Please try again. Error: {}".format(str(e)))
                else:
                    bp.save()
                    new_periods.append(bp)

                for group in billing_groups:
                    bpcpa = BillingPeriodCustomPaymentAmount()
                    bpcpa.group = group
                    bpcpa.period = bp
                    try:
                        if post['invoice_amount_group{}{}'.format(group.pk, bp_id)] is None:
                            bpcpa.invoice_amount = Decimal('0.00')
                        else:
                            bpcpa.invoice_amount = post['invoice_amount_group{}{}'.format(group.pk, bp_id)]
                    except KeyError as e:
                        alert_messages.append("Field not found for NEW billing period. Error: {}".format(str(e)))
                        continue

                    try:
                        bpcpa.full_clean()
                    except ValidationError as e:
                        error_messages.append("Invalid data in new row, for group amount set for '{}' price. Please try again. Error: {}".format(group.name, str(e)))
                    else:
                        bpcpa.save()

            elif existing_match:
                # Update an EXISTING billing period
                # If there are attached invoices you can update the due_date by
                #   just changing it here.
                bp_id = '{}'.format(existing_match.group(1))
                bp_pk = existing_match.group(1)
                changed = False

                try:
                    bp = BillingPeriod.objects.get(pk=bp_pk)
                except BillingPeriod.DoesNotExist as e:
                    error_messages.append("Not able to find Billing Period with ID #{}. Error: {}".format(bp_pk, str(e)))

                # Check if user currently has access to this billing period.
                # If the current viewing league matches (already checked),
                # allow them access.
                # If they don't have access then just continue silently, I guess.
                # TODO: do something else if there's a permissions issue?
                if bp.league.pk != self.league.pk:
                    error_messages.append("You don't seem to have permission to access a Billing Period in this form. Not sure how that happened. I can't save it.")

                try:
                    new_invoice_date = datetime.strptime(
                        post['invoice_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                except KeyError as e:
                    alert_messages.append("Field not found for '{}' when saving billing period. Field was 'invoice_date{}'' . Error: {}".format(bp, bp_id, str(e)))
                except ValueError as e:
                    error_messages.append("Invalid date specified for invoice date for '{}'. Value was '{}'. Error: {}".format(bp, post['invoice_date{}'.format(bp_id)], str(e)))
                if new_invoice_date.date() != bp.invoice_date:
                    # If the invoice date has already passed, do not allow them to update it.
                    if timezone.now().date() < bp.invoice_date:
                        changed = True
                        bp.invoice_date = new_invoice_date
                    else:
                        alert_messages.append("You cannot update invoice date for '{}'. The date has already passed.".format(bp))

                try:
                    new_due_date = datetime.strptime(
                        post['due_date{}'.format(bp_id)],
                        '%m/%d/%y'
                    )
                except KeyError as e:
                    alert_messages.append("Field not found for '{}' when saving billing period. Field was 'invoice_date{}'' . Error: {}".format(bp, bp_id, str(e)))
                except ValueError as e:
                    error_messages.append("Invalid date specified for due date for '{}'. Value was '{}'. Error: {}".format(bp, post['invoice_date{}'.format(bp_id)], str(e)))
                if new_due_date.date() != bp.due_date:
                    # If the due date has already passed, do not allow them to update it.
                    if timezone.now().date() < bp.due_date:
                        changed = True
                        bp.due_date = new_due_date
                    else:
                        alert_messages.append("You cannot update due date for '{}'. The date has already passed.".format(bp))

                try:
                    new_start_date = datetime.strptime(
                        post['start_date{}'.format(bp_id)],
                        '%m/%d/%y',
                    )
                    new_end_date = datetime.strptime(
                        post['end_date{}'.format(bp_id)],
                        '%m/%d/%y',
                    )
                    new_name = post['name{}'.format(bp_id)]
                except KeyError as e:
                    alert_messages.append("Field not found for '{}' when saving billing period. Error: {}".format(bp, str(e)))

                if new_start_date.date() != bp.start_date:
                    changed = True
                    bp.start_date = new_start_date
                if new_end_date.date() != bp.end_date:
                    changed = True
                    bp.end_date = new_end_date
                if new_name != bp.name:
                    changed = True
                    bp.name = new_name

                try:
                    bp.full_clean()
                except ValidationError as e:
                    error_messages.append("Unable to validate and save billing period '{}'. Error: {}".format(bp, str(e)))
                else:
                    if changed:
                        bp.save()

                for group in billing_groups:
                    bpcpa_id = 'invoice_amount_group{}{}'.format(group.pk, bp_id)
                    try:
                        bpcpa = BillingPeriodCustomPaymentAmount.objects.get(
                            group=group.pk,
                            period=bp,
                        )
                    except BillingPeriodCustomPaymentAmount.DoesNotExist:
                        bpcpa = BillingPeriodCustomPaymentAmount()
                        bpcpa.group = group
                        bpcpa.period = bp
                    try:
                        if post['invoice_amount_group{}_{}'.format(group.pk, bp_id)] is None:
                            new_invoice_amount = Decimal('0.00')
                        else:
                            new_invoice_amount = Decimal(post['invoice_amount_group{}_{}'.format(group.pk, bp_id)])
                    except KeyError as e:
                        alert_messages.append("Field not found saving invoice amount for group '{}' in billing period '{}'. Field was supposed to be '{}'. Error: {}".format(group.name, bp.name, 'invoice_amount_group{}_{}'.format(group.pk, bp_id), str(e)))
                        continue
                    except InvalidOperation as e:
                        error_messages.append("Invalid decimal value found when saving invoice amount for group '{}' in billing period '{}'. Please check it and fix it. Error: {}".format(group.name, bp.name, 'invoice_amount_group{}_{}'.format(group, bp), str(e)))
                        continue

                    # It has not changed, lets just move on from here...
                    if new_invoice_amount == bpcpa.invoice_amount:
                        continue

                    changed = True
                    bpcpa.invoice_amount = new_invoice_amount

                    try:
                        bpcpa.full_clean()
                    except ValidationError as e:
                        error_messages.append("Unable to validate and save invoice amount for group '{}' in billing period '{}'. Error: {}".format(group.name, bp, str(e)))
                    else:
                        bpcpa.save()

                if changed:
                    updated_periods.append(bp)

            elif delete_match:
                # Delete an EXISTING billing period
                # But only if there are no invoices attached.
                # Verify user has access to this billing period
                bp_pk = delete_match.group(1)

                try:
                    bp = BillingPeriod.objects.get(pk=bp_pk)
                except BillingPeriod.DoesNotExist as e:
                    error_messages.append("Not able to find Billing Period with ID #{}. Error: {}".format(bp_pk, str(e)))

                if bp.league.pk != self.league.pk:
                    error_messages.append("You don't seem to have permission to delete a Billing Period in this form. Not sure how that happened. I can't delete it.")

                # TODO verify no invoices (haven't dev'd the model yet...)

                bp.delete()
                deleted_periods.append(bp)

        success_message = []
        if new_periods:
            success_message.append("Added {} new billing periods.".format(len(new_periods)))
        if updated_periods:
            success_message.append("Updated {} billing periods.".format(len(updated_periods)))
        if deleted_periods:
            success_message.append("Deleted {} billing periods.".format(len(deleted_periods)))

        if success_message:
            messages.success(request, "<h2>Saved Form</h2><p>{}</p>".format("</p><p>".join(success_message)))
            print(success_message)
        if error_messages:
            messages.error(request, "<h2>Errors</h2><ul><li>{}</li></ul>".format("</li><li>".join(error_messages)))
            print(error_messages)
        if alert_messages:
            messages.warning(request, "<h2>Errors</h2><ul><li>{}</li></ul>".format("</li><li>".join(alert_messages)))
            print(alert_messages)

        print(success_message)
        return HttpResponseRedirect(
            reverse("registration:event_admin_billing_periods", kwargs={'event_slug': self.event.slug}))
