from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views import View

from .models import RegistrationEvent, RegistrationInvite


class RegistrationBegin(View):
    def get(self, request, event_slug, uuid=None):
        event = get_object_or_404(RegistrationEvent, slug=event_slug)

        if uuid:
            invite = get_object_or_404(RegistrationInvite, uuid=uuid)

            if invite.user:
                # User attached to this invite, require login

                if not request.user.is_authenticated:
                    return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
                
                if invite.user != request.user:
                    # Different user is attached to this invite compared to whom is logged in
                    # TODO useful message here?
                    return HttpResponse(status=403)

        else:
            # Check if event is available to be registered by the public
            if (event.public_registration_open_date and \
                event.public_registration_open_date >= timezone.now()) \
                or \
                (event.public_registration_closes_date and \
                event.public_registration_closes_date <= timezone.now()):

                # Registration closed to the public currently
                # TODO helpful message here?
                return HttpResponse(status=404)

        # No user attached to this invite, they need to register for an account
        
        # If logged in, go to the registration form
        # If not logged in, user needs to create an account