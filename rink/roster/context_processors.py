from billing.models import Invoice, BillingSubscription


def roster_billing_badges(request):
    try:
        if 'roster' in request.resolver_match.namespaces:
            pass
        else:
            return {}
    except AttributeError:
        return {}

    league_id = request.session.get('view_league', None)
    user_id = request.resolver_match.kwargs.get('pk', None)

    if league_id and user_id:
        unpaid_invoices = Invoice.objects.filter(
            user__pk=user_id,
            league__pk=league_id,
            status='unpaid'
        ).count()

        active_subscriptions = BillingSubscription.objects.filter(
            user__pk=user_id,
            league__pk=league_id,
            status='active',
        ).count()

        if unpaid_invoices == 0:
            unpaid_invoices = None
        if active_subscriptions == 0:
            active_subscriptions = None

        return {
            'unpaid_invoice_count': unpaid_invoices,
            'active_subscription_count': active_subscriptions,
        }
    else:
        return {}

