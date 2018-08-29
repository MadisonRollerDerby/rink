from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from .forms import UpdateStripeCardForm, PayNowForm
from .models import UserStripeCard, Invoice, BillingPeriod
from league.models import League

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
        )

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

