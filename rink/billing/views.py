from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from .forms import UpdateStripeCardForm, PayNowForm, InvoiceFilterForm
from .models import UserStripeCard, Invoice, BillingPeriod
from .tables import InvoiceTable
from league.mixins import RinkLeagueAdminPermissionRequired
from league.models import League

from django_tables2 import SingleTableView
from stripe.error import CardError


class PayView(LoginRequiredMixin, View):
    template_name = "billing/pay.html"

    def get(self, request):
        try:
            user_stripe_card = UserStripeCard.objects.get(user=request.user)
        except UserStripeCard.DoesNotExist:
            user_stripe_card = None

        invoices = Invoice.objects.filter(
            user=request.user,
            league=League.objects.get(pk=request.session['view_league']),
            status='unpaid',
        )

        future_invoices = BillingPeriod.objects.filter(
            event__league=League.objects.get(pk=request.session['view_league']),
            event__billingsubscription__user=request.user,
            event__billingsubscription__status='active',
            invoice_date__gte=timezone.now(),
        ).distinct()

        for invoice in future_invoices:
            invoice.invoice_amount = invoice.get_invoice_amount(user=request.user)

        return render(request, self.template_name, {
            'invoices': invoices,
            'future_invoices': future_invoices,
            'user_stripe_card': user_stripe_card,
            'current_time': timezone.now(),
        })

    def post(self, request):
        # I suppose we could show form errors here, but whatever
        form = PayNowForm(data=request.POST)

        if form.is_valid():
            try:
                user_stripe_card = UserStripeCard.objects.get(user=request.user)
            except UserStripeCard.DoesNotExist:
                messages.error(request, "You do not have a credit card saved. Please save a credit card before attempting to pay an invoice. Sorry. Thanks.")
                return redirect('billing:pay')

            try:
                invoice = Invoice.objects.get(
                    pk=form.cleaned_data['invoice_id'],
                    user=request.user,
                    league=League.objects.get(pk=request.session['view_league']),
                    status='unpaid',
                )
            except Invoice.DoesNotExist:
                return redirect('billing:pay')

            try:
                user_stripe_card.charge(invoice=invoice)
                messages.success(request, "<strong>>Payment successful!</strong> We emailed you a receipt. Thanks.</p>")
            except CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.error(request, "<p>We were unable to charge your credit card.</p>\
                    <p>Reason: {}</p>\
                    <p>Please try again or contact us if you continue to have issues.</p>".format(
                    err.get('message')))

        return redirect('billing:pay')


class PaymentHistoryView(LoginRequiredMixin, View):
    template_name = "billing/payment_history.html"

    def get(self, request):
        invoices = Invoice.objects.filter(
            user=request.user,
            league=League.objects.get(pk=request.session['view_league']),
        ).exclude(status='unpaid')

        return render(request, self.template_name, {
            'invoices': invoices,
        })


class UpdateUserStripeCardView(LoginRequiredMixin, View):
    template_name = "billing/update_card.html"

    def get(self, request):
        try:
            user_stripe_card = UserStripeCard.objects.get(user=request.user)
        except UserStripeCard.DoesNotExist:
            user_stripe_card = None

        return render(request, self.template_name, {
            'user_stripe_card': user_stripe_card,
        })

    def post(self, request):
        form = UpdateStripeCardForm(data=request.POST)
        if form.is_valid():
            card_profile, created = UserStripeCard.objects.get_or_create(
                user=request.user,
                league=League.objects.get(pk=request.session['view_league']),
            )

        try:
            card_profile.update_from_token(form.cleaned_data['stripe_token'])
            #payment = card_profile.charge(invoice=invoice, send_receipt=False)
            messages.success(request, "Card on file has been updated. Thanks!")
        except CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(request, "<p>We were unable to save your credit card.</p>\
                <p>Reason: {}</p>\
                <p>Please try again or contact us if you continue to have issues.</p>".format(
                err.get('message'))
            )
        return redirect('billing:update_card')


class BillingAdminView(RinkLeagueAdminPermissionRequired, SingleTableView):
    template_name = "billing/billing_admin.html"
    table_class = InvoiceTable
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        data = None
        if request.GET.get('filtered', None):
            data = request.GET
        self.filter_form = InvoiceFilterForm(data=data)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # https://stackoverflow.com/a/29149972
        q_status = None
        q_search = None

        if self.filter_form.is_valid():
            status_filters = ['paid', 'unpaid', 'refunded', 'canceled']
            for status in status_filters:
                if self.filter_form.cleaned_data[status]:
                    if not q_status:
                        q_status = Q()
                    q_status.add(Q(status=status), Q.OR)
            
            search = self.filter_form.cleaned_data['search']
            if search:
                q_search = Q()
                q_search.add(Q(user__first_name__icontains=search), Q.OR)
                q_search.add(Q(user__last_name__icontains=search), Q.OR)
                q_search.add(Q(user__derby_name__icontains=search), Q.OR)
                q_search.add(Q(user__email__icontains=search), Q.OR)
                q_search.add(Q(description__icontains=search), Q.OR)
                q_search.add(Q(pk=search), Q.OR)

        q_all = Q(league_id=self.request.session['view_league'])
        if q_status and q_search:
            q_all &= q_status & q_search
        elif q_status:
            q_all &= q_status
        elif q_search:
            q_all &= q_search

        return Invoice.objects.filter(q_all).distinct()

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context
