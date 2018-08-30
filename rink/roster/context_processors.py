from billing.models import Invoice


def unpaid_invoice_count(request):
    league_id = request.session.get('view_league', None)
    count = None

    if league_id and hasattr(request, 'resolver_match'):
        user_id = request.resolver_match.kwargs.get('pk')
        count = Invoice.objects.filter(
            league__pk=league_id,
            status='unpaid'
        ).count()

    return {'unpaid_invoice_count': count}

