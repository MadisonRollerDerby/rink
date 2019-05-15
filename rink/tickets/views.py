from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from league.models import League
from league.utils import send_email
from .models import TicketEvent, TicketPurchase
from .forms import TicketForm

import stripe




class TicketPurchaseView(View):
    def get(self, request, league_slug, event_slug):
        league = get_object_or_404(League, slug=league_slug)
        event = get_object_or_404(TicketEvent, slug=event_slug)

        return render(request, 'tickets/tickets.html', {
                'league_template': league,
                'league': league,
                'event': event,
            }
        )  

    def post(self, request, league_slug, event_slug):
        league = get_object_or_404(League, slug=league_slug)
        event = get_object_or_404(TicketEvent, slug=event_slug)

        form = TicketForm(request.POST)
        if form.is_valid():
            # charge token five bucks
            stripe.api_key = league.get_stripe_private_key()
            stripe.api_version = settings.STRIPE_API_VERSION

            try:
                customer = stripe.Customer.create(
                    description=form.cleaned_data.get('derby_name'),
                    name=form.cleaned_data.get('real_name'),
                    email=form.cleaned_data.get('email'),
                    source=form.cleaned_data.get('stripe_token'),
                )

                charge = stripe.Charge.create(
                    amount=500,
                    currency='usd',
                    description=event.name,
                    customer=customer,
                )
            except stripe.error.CardError as e:
                body = e.json_body
                error = body.get('error', {})
            except:
                error = "A generic error happened when trying to charge your card. Weird."
            else:
                ticket = TicketPurchase.objects.create(
                    event=event,
                    real_name=form.cleaned_data.get('real_name'),
                    derby_name=form.cleaned_data.get('derby_name'),
                    email=form.cleaned_data.get('email'),
                    transaction_id=charge.id,
                    amount=5.00,
                )

                send_email(
                    league=league,
                    to_email=form.cleaned_data.get('email'),
                    template="ticket",
                    context={
                        'ticket': ticket,
                        'event': event,
                    },
                )

                return redirect('tickets:ticket_purchase_done', league_slug=league_slug, event_slug=event_slug)
        else:
            error = form.errors

        return render(request, 'tickets/tickets.html', {
                'league_template': league,
                'league': league,
                'event': event,
                'error': error,
            }
        )  


class TicketPurchaseDoneView(View):
    def get(self, request, league_slug, event_slug):
        league = get_object_or_404(League, slug=league_slug)
        event = get_object_or_404(TicketEvent, slug=event_slug)

        return render(request, 'tickets/done.html', {
                'league_template': league,
                'league': league,
                'event': event,
            }
        )  
