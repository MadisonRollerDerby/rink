
from django.contrib import messages
from django.db.models import Q, Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, UpdateView, ListView, FormView

from django_tables2 import SingleTableView
from django_filters.views import FilterView
from guardian.shortcuts import get_users_with_perms, remove_perm, get_perms

from billing.forms import QuickPaymentForm, QuickInvoiceForm, QuickRefundForm
from billing.models import (
    Invoice, BillingGroupMembership, BillingGroup, BillingSubscription, Payment,
    UserStripeCard)
from league.mixins import RinkLeagueAdminPermissionRequired
from legal.models import LegalSignature
from registration.models import RegistrationData, Roster, RegistrationInvite
from taskapp.celery import app as celery_app
from users.models import User, Tag, UserTag, UserLog

from .forms import (RosterProfileForm, BillingGroupForm,
    RosterFilterForm, RosterAddNoteForm, RosterCreateInvoiceForm,
    RosterMembershipRemoveMembership)
from .resources import RosterResource
from .tables import RosterTable


class RosterList(RinkLeagueAdminPermissionRequired, SingleTableView, FilterView):
    template_name = 'roster/list.html'
    paginate_by = 50
    table_class = RosterTable
    filter_form = None

    def get(self, request, *args, **kwargs):
        if request.GET.get('csv', None):
            roster = RegistrationData.objects.filter(organization__league=self.league)
            roster_resource = RosterResource()
            dataset = roster_resource.export(queryset=roster)
            response = HttpResponse(dataset.csv, content_type='text/csv')
            response['Content-Disposition'] = 'attachment;filename=Roster-{}-{}.csv'.format(self.league.name, timezone.now().date())
            return response

        return super().get(request, *args, **kwargs)

    def get_filter_form(self):
        if not self.filter_form:
            data = None
            session_filter = self.request.session.get('admin_roster_filter', None)

            if self.request.GET.get('filtered', None):
                data = self.request.GET
                self.request.session['admin_roster_filter'] = data

            if not data and session_filter:
                data = session_filter

            self.filter_form = RosterFilterForm(data=data, league=self.league)

        return self.filter_form

    def get_queryset(self):
        # https://stackoverflow.com/a/29149972
        filter_form = self.get_filter_form()
        q_all = Q()

        if filter_form.is_valid():
            # SEARCH BOX
            # match names, emails, maybe other things
            search = filter_form.cleaned_data['search']
            if search:
                q_search = Q()
                q_search.add(Q(first_name__icontains=search), Q.OR)
                q_search.add(Q(last_name__icontains=search), Q.OR)
                q_search.add(Q(derby_name__icontains=search), Q.OR)
                q_search.add(Q(email__icontains=search), Q.OR)
                q_search.add(Q(invoice__description__icontains=search), Q.OR)
                if search.isdigit():
                    q_search.add(Q(invoice__pk=search), Q.OR)
                q_all.add(q_search, Q.AND)

            # BILLING FILTERS
            # invoice due, invoice overdue
            unpaid = filter_form.cleaned_data['unpaid_invoice']
            invoice_overdue = filter_form.cleaned_data['invoice_overdue']

            if unpaid:
                q_all.add(Q(invoice__status='unpaid'), Q.AND)

            if invoice_overdue:
                q_overdue = Q()
                q_overdue.add(Q(invoice__status='unpaid'), Q.AND)
                q_overdue.add(Q(invoice__due_date__lte=timezone.now()), Q.AND)
                q_all.add(q_overdue, Q.AND)

            # USER TAGS
            # match users tagged with admin-defined tags names
            q_tags = None
            for tag in Tag.objects.filter(league=self.league):
                if filter_form.cleaned_data.get('tag{}'.format(tag.pk), None):
                    if not q_tags:
                        q_tags = Q()
                    q_tags.add(Q(tags__pk=tag.pk), Q.OR)
            if q_tags:
                q_all.add(q_tags, Q.AND)

            # BILLING GROUPS
            # Billing Group filters the are league-wide for determining billing amount
            q_bg = None
            for bg in BillingGroup.objects.filter(league=self.league):
                if filter_form.cleaned_data.get('billing_group{}'.format(bg.pk), None):
                    if not q_bg:
                        q_bg = Q()

                    # Default group, search for:
                    # - billing group membership is null
                    # - OR the billing group membership is there
                    if bg.default_group_for_league:
                        q_bg.add(
                            Q(billinggroupmembership__isnull=True) | Q(billinggroupmembership__group__pk=bg.pk),
                            Q.OR)
                    # Not the default group, just search for it by group PK:
                    else:
                        q_bg.add(Q(billinggroupmembership__group__pk=bg.pk), Q.OR)

            if q_bg:
                q_all.add(q_bg, Q.AND)

        queryset = get_users_with_perms(self.league)
        if q_all != Q():
            return queryset.filter(q_all)
        else:
            return queryset

    def get_context_data(self, **kwargs):
        additional_context = {
            'filter_form': self.get_filter_form(),
        }
        return {**super().get_context_data(**kwargs), **additional_context}


class RosterAdminProfile(RinkLeagueAdminPermissionRequired, UpdateView):
    template_name = 'roster/admin_profile.html'
    model = User
    form_class = RosterProfileForm

    def get_success_url(self):
        messages.success(self.request, "Saved profile details.")
        return reverse('roster:admin_profile', kwargs={'pk': self.kwargs['pk']})


class RosterAdminEvents(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = 'roster/admin_events.html'
    model = User

    def get_context_data(self, **kwargs):
        additional_context = {
            'event_signups': RegistrationData.objects.filter(
                user=self.object,
                event__league=self.league,
            ),
        }
        return {**super().get_context_data(**kwargs), **additional_context}


class RosterAdminBilling(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = "roster/admin_billing.html"
    model = Invoice

    def get_object(self, queryset=None):
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        invoice_id = self.kwargs.get('invoice_id', None)
        if not invoice_id:
            try:
                return Invoice.objects.filter(
                    league=self.league,
                    user=user,
                ).order_by('-invoice_date').first()
            except Invoice.ObjectDoesNotExist:
                return None

        invoice = get_object_or_404(Invoice, pk=invoice_id, user=user)
        return invoice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        if self.object:
            try:
                context['payment'] = self.object.payment
            except AttributeError:
                context['payment'] = None

            context['payment_form'] = QuickPaymentForm(initial={'amount': self.object.invoice_amount})
            context['invoice_form'] = QuickInvoiceForm(instance=self.object)
            context['refund_form'] = QuickRefundForm(initial={'refund_amount': self.object.invoice_amount})

        context['user'] = user
        context['invoices'] = Invoice.objects.filter(league=self.league, user=user).order_by('-invoice_date')
        context['billing_group_form'] = BillingGroupForm(league=self.league, user=user)
        context['create_invoice_form'] = RosterCreateInvoiceForm(initial={
            'invoice_amount': 0,
            'invoice_date': timezone.now(),
            'due_date': timezone.now() + timezone.timedelta(days=7),
        })
        return context


class RosterAdminSubscriptionsList(RinkLeagueAdminPermissionRequired, ListView):
    template_name = 'roster/admin_subscriptions.html'
    model = BillingSubscription

    def get_context_data(self, **kwargs):
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        inactive_subscriptions = BillingSubscription.objects.filter(
            league=self.league,
            user=user,
        ).exclude(
            status='active'
        ).select_related('event').annotate(
            billing_period_count=Count('event__billingperiod__pk'),
        ).annotate(
            invoice_count=Count('invoice'),
        )

        return {
            **super().get_context_data(**kwargs),
            **{'inactive_subscriptions': inactive_subscriptions, 'user': user}
        }

    def get_queryset(self):
        return BillingSubscription.objects.filter(
            league=self.league,
            user=get_object_or_404(User, pk=self.kwargs['pk']),
            status='active',
        ).select_related('event').annotate(
            billing_period_count=Count('event__billingperiod__pk'),
        ).annotate(
            invoice_count=Count('invoice'),
        )


class RosterAdminSubscriptionsDeactivate(RinkLeagueAdminPermissionRequired, View):
    def get(self, request, *args, **kwargs):
        subscription = get_object_or_404(BillingSubscription,
            pk=kwargs['subscription_id'],
            league=self.league,
            user=get_object_or_404(User, pk=kwargs['pk']),
        )

        if subscription.status == 'active':
            messages.success(request, "Subscription deactivated.")
            subscription.deactivate()
        else:
            messages.error(request, "Subscription has already been deactivated.")

        return redirect('roster:admin_subscriptions', pk=kwargs['pk'])


class RosterAdminCreateInvoice(RinkLeagueAdminPermissionRequired, FormView):
    form_class = RosterCreateInvoiceForm

    def form_valid(self, form):
        self.invoice = form.save(commit=False)
        self.invoice.user = get_object_or_404(User, pk=self.kwargs['pk'])
        self.invoice.league = self.league
        self.invoice.save()

        if form.cleaned_data['send_email']:
            celery_app.send_task('billing.tasks.email_invoice',
                args=[self.invoice.pk], kwargs={})

        return self.success_url()

    def success_url(self):
        return redirect('roster:admin_billing_invoice', pk=self.kwargs['pk'], invoice_id=self.invoice.pk)

    def get(self):
        return self.success_url()


class RosterAdminBillingGroup(RinkLeagueAdminPermissionRequired, View):
    def get(self, request, *args, **kwargs):
        raise Http404("Invalid request")

    def post(self, request, *args, **kwargs):
        self.user = get_object_or_404(User, pk=kwargs['pk'])

        form = BillingGroupForm(
            data=request.POST,
            league=self.league,
            user=self.user,
        )

        if form.is_valid():
            selected_group = get_object_or_404(BillingGroup,
                pk=form.cleaned_data['billing_group'].pk, league=self.league)
            membership, created = BillingGroupMembership.objects.get_or_create(
                league=self.league,
                user=self.user,
                defaults={'group': selected_group},
            )
            membership.group = selected_group
            membership.save()

            try:
                default_group_for_league = BillingGroup.objects.get(
                    league=self.league,
                    default_group_for_league=True,
                )
            except BillingGroup.DoesNotExist:
                default_group_for_league = None

            # If this is the default group for the league, dont allow
            # them to set anything in the event they want to mass-change the
            # group later and a few stragglers are hard-set.
            if membership.group == default_group_for_league:
                membership.delete()

            messages.success(self.request, "Saved billing group selection.")
        else:
            messages.error(self.request, "Unable to save group, invalid selection for some reason. Weird.")

        return redirect('roster:admin_billing', pk=self.kwargs['pk'])


class RosterAdminLegal(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = 'roster/admin_legal.html'
    model = User

    def get_context_data(self, **kwargs):
        additional_context = {
            'registration_data': RegistrationData.objects.filter(
                user=self.object,
                event__league=self.league,
            ),
        }
        return {**super().get_context_data(**kwargs), **additional_context}


class RosterAdminTags(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = 'roster/admin_tags.html'
    model = User

    def get_context_data(self, **kwargs):
        tag_ids = []
        for user_tag in UserTag.objects.filter(tag__league=self.league, user=self.object):
            tag_ids.append(user_tag.tag.pk)

        additional_context = {
            'league_tags': Tag.objects.filter(
                league=self.league,
            ),
            'user_tags': tag_ids,
        }
        return {**super().get_context_data(**kwargs), **additional_context}

    def post(self, request, *args, **kwargs):
        # Ugly way to process this form, I guess, kinda.... un-django-like
        # But here we go:

        user = get_object_or_404(User, pk=kwargs.get('pk', None))
        # Clear out all existing tags for this user
        UserTag.objects.filter(user=user, tag__league=self.league).delete()

        # Add the tags that we've checked here
        for key, value in request.POST.items():
            if key.startswith("tag"):
                try:
                    tag = Tag.objects.filter(league=self.league, pk=value).get()
                except Tag.DoesNotExist:
                    pass
                    # ehhhhhhhh, yeah
                else:
                    user_tag_obj, user_tag_created = UserTag.objects.get_or_create(
                        user=user,
                        tag=tag,
                    )

        messages.success(self.request, "User tags saved.")
        return redirect('roster:admin_tags', pk=user.pk)


class RosterAdminUserLog(RinkLeagueAdminPermissionRequired, ListView):
    template_name = 'roster/admin_notes.html'
    model = UserLog

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **{'note_form': RosterAddNoteForm()}
        }

    def get_queryset(self):
        return UserLog.objects.filter(
            league=self.league,
            user=get_object_or_404(User, pk=self.kwargs['pk']),
        )


class RosterAdminAddMessageUserLog(RinkLeagueAdminPermissionRequired, FormView):
    form_class = RosterAddNoteForm

    def form_valid(self, form):
        user = get_object_or_404(User, pk=self.kwargs['pk'])

        UserLog.objects.create(
            user=user,
            league=self.league,
            message=form.cleaned_data['message'],
            admin_user=self.request.user,
        )

        return self.success_url()

    def success_url(self):
        return redirect('roster:admin_notes', pk=self.kwargs['pk'])

    def get(self):
        return self.success_url()


class RosterAdminMembership(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = 'roster/admin_membership.html'
    model = User

    def get_context_data(self, **kwargs):
        additional_context = {
            'active_rosters': Roster.objects.filter(
                user=self.object,
                event__league=self.league,
                event__end_date__gt=timezone.now(),
            ),
            'remove_roster_form': RosterMembershipRemoveMembership(),
        }
        return {**super().get_context_data(**kwargs), **additional_context}


class RosterAdminRemoveFromRoster(RinkLeagueAdminPermissionRequired, View):
    def get(self, request, *args, **kwargs):
        raise Http404("Invalid request")

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])

        form = RosterMembershipRemoveMembership(request.POST)
        if form.is_valid():
            roster = get_object_or_404(Roster,
                pk=form.cleaned_data['roster_id'],
                user=user,
                event__league=self.league,
            )
            event_name = roster.event.name
            roster_pk = roster.pk

            try:
                subscription = BillingSubscription.objects.get(
                    roster=roster,
                    league=self.league,
                    user=user,
                )
            except BillingSubscription.DoesNotExist:
                pass
            else:
                if subscription.active:
                    subscription.deactivate()
                    messages.success(request, "Billing Subscription deactivated for roster entry. (SUB #{})".format(subscription.pk))

            roster.delete()
            messages.success(request, "Removed {} from roster for {}. (ROSTER #{})".format(
                user,
                event_name,
                roster_pk,
            ))

        return redirect('roster:admin_membership', pk=self.kwargs['pk'])


class RosterAdminDeactivateUser(RinkLeagueAdminPermissionRequired, View):
    def get(self, request, *args, **kwargs):
        raise Http404("Invalid request")

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])

        # Cancel all unpaid invoices
        Invoice.objects.filter(
            user=user,
            league=self.league,
            status='unpaid',
        ).update(status='canceled')

        # Remove from all active event rosters
        Roster.objects.filter(
            user=user,
            event__league=self.league,
            event__end_date__gt=timezone.now(),
        ).delete()

        # Cancel all active subscriptions
        subscriptions = BillingSubscription.objects.filter(
            user=user,
            league=self.league,
            status='active',
        )
        for subscription in subscriptions:
            subscription.deactivate()

        # Set user back to default billing group
        BillingGroupMembership.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        messages.success(request, "User {} has been made inactive.".format(user))
        return redirect('roster:admin_membership', pk=self.kwargs['pk'])


class RosterAdminDeleteUser(RinkLeagueAdminPermissionRequired, View):
    def get(self, request, *args, **kwargs):
        raise Http404("Invalid request")

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])
        user_name = str(user)

        if request.user.pk == user.pk:
            messages.error(request, "You cannot delete yourself. Sorry. That would be weird.")
            return redirect('roster:admin_membership', pk=self.kwargs['pk'])


        # Billing Subscriptions
        BillingSubscription.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # Invoices
        Invoice.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # Payments
        Payment.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # Saved Cards
        UserStripeCard.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # Custom Billing Groups
        BillingGroupMembership.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # Roster
        Roster.objects.filter(
            user=user,
            event__league=self.league,
        ).delete()

        # Registration Data
        RegistrationData.objects.filter(
            user=user,
            event__league=self.league,
        ).delete()

        # Registration Invites
        RegistrationInvite.objects.filter(
            user=user,
            event__league=self.league,
        ).delete()

        # Legal Signatures
        # I suppose these could be emailed as a backup before they are deleted.
        # Seems like something we wouldn't want to lose?
        LegalSignature.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # User Logs
        UserLog.objects.filter(
            user=user,
            league=self.league,
        ).delete()

        # User Tags
        # currently no League field (uh... huh?) Can't delete now.

        # Remove permissions
        for perm in get_perms(user, self.league):
            remove_perm(perm, user, self.league)
        for perm in get_perms(user, self.league.organization):
            remove_perm(perm, user, self.league.organization)

        if BillingSubscription.objects.filter(user=user).exists() or \
            Invoice.objects.filter(user=user).exists() or \
            Payment.objects.filter(user=user).exists() or \
            UserStripeCard.objects.filter(user=user).exists() or \
            BillingGroupMembership.objects.filter(user=user).exists() or \
            Roster.objects.filter(user=user).exists() or \
            RegistrationData.objects.filter(user=user).exists() or \
            RegistrationInvite.objects.filter(user=user).exists() or \
            LegalSignature.objects.filter(user=user).exists() or \
            UserLog.objects.filter(user=user).exists():

                # User still exists in the system. Maybe we should care.
                pass
        else:
            messages.success(request, "<strong>{}</strong> is not a member of any other leagues on the system. They have been completely removed.".format(user_name))
            user.delete()

        messages.success(request, "Deleted user <strong>{}</strong> from database. They are now gone.".format(user_name))
        return redirect('roster:list')
