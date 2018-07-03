from django.shortcuts import render
from django.http import HttpResponse
from django.views import View

from registration.forms import RegistrationForm
from registration.models import RegistrationData


class RegistrationBegin(View):
    def get(self, request, registration_slug, invite_key=None):
        #return HttpResponse("{}, {}".format(registration_slug, invite_key))

        registration_form = RegistrationForm

        return render(request, 'registration/registration.html', {
                'registration_form': registration_form
            }
        )