from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, UpdateView, FormView

from .forms import InvoiceFilterForm, QuickPaymentForm, QuickInvoiceForm, QuickRefundForm
from .models import Invoice
from .tables import InvoiceTable
from league.mixins import RinkLeagueAdminPermissionRequired

from django_tables2 import SingleTableView


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
                if search.isdigit():
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


class BillingAdminDetailView(RinkLeagueAdminPermissionRequired, DetailView):
    template_name = "billing/billing_admin_detail.html"
    model = Invoice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment'] = self.object.payment
        context['user'] = self.object.user
        context['payment_form'] = QuickPaymentForm(initial={'amount': self.object.invoice_amount})
        context['invoice_form'] = QuickInvoiceForm(instance=self.object)
        context['refund_form'] = QuickRefundForm(initial={'refund_amount': self.object.invoice_amount})
        return context


class BillingAdminInvoiceEditView(View):
    def get_invoice_admin_url(self, pk):
        return redirect('billing:billing_admin_detail', pk=pk)

    def get(self, request, *args, **kwargs):
        return self.get_invoice_admin_url(kwargs['pk'])


class BillingAdminAddPaymentView(RinkLeagueAdminPermissionRequired, BillingAdminInvoiceEditView):
    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=kwargs['pk'])
        form = QuickPaymentForm(request.POST)

        if invoice.payment:
            messages.error(request, "This invoice already has a payment.")
        elif not form.is_valid():
            messages.error(request, form.errors)
        else:
            try:
                invoice.pay(
                    amount=form.cleaned_data['amount'],
                    processor=form.cleaned_data['processor'],
                    transaction_id=form.cleaned_data['transaction_id'],
                    payment_date=form.cleaned_data['payment_date'],
                )
                messages.success(request, "Invoice payment added.")
            except ValueError as e:
                messages.error(request, e)
        return self.get_invoice_admin_url(kwargs['pk'])


class BillingAdminRefundPaymentView(RinkLeagueAdminPermissionRequired, BillingAdminInvoiceEditView):
    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=self.kwargs['pk'])
        form = QuickRefundForm(request.POST)
        if not invoice.payment:
            messages.error(request, "No payment is associated with this invoice.")
        elif not form.is_valid():
            messages.error(request, form.errors)
        else:
            try:
                invoice.payment.refund(
                    amount=form.cleaned_data['refund_amount'],
                    refund_reason=form.cleaned_data['refund_reason'],
                )
                messages.success(request, "Payment refunded successfully.")
            except ValueError as e:
                messages.error(request, e)
        return self.get_invoice_admin_url(kwargs['pk'])


class BillingAdminEditInvoiceView(RinkLeagueAdminPermissionRequired, BillingAdminInvoiceEditView):
    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=self.kwargs['pk'])
        form = QuickInvoiceForm(data=request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice saved.")
        else:
            messages.error(request, form.errors)
        return self.get_invoice_admin_url(kwargs['pk'])
