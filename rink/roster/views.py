from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, UpdateView

from django_tables2 import SingleTableView
from django_filters.views import FilterView
from guardian.shortcuts import get_users_with_perms

from billing.forms import QuickPaymentForm, QuickInvoiceForm, QuickRefundForm
from billing.models import Invoice, BillingGroupMembership, BillingGroup
from league.mixins import RinkLeagueAdminPermissionRequired
from registration.models import RegistrationData
from users.models import User, Tag, UserTag

from .forms import RosterProfileForm, BillingGroupForm, RosterFilterForm
from .tables import RosterTable


class RosterList(RinkLeagueAdminPermissionRequired, SingleTableView, FilterView):
    template_name = 'roster/list.html'
    paginate_by = 50
    table_class = RosterTable
    filter_form = None

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
        return context


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

