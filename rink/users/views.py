from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from league.models import League
# Can't seem to do .forms or .models, some kind of import issue...
from users.forms import UserProfileForm
from users.models import User
from users.tasks import notify_admin_of_user_changes

from guardian.shortcuts import get_objects_for_user


class UserProfileView(LoginRequiredMixin, View):
    template_name = "users/rink_profile_update.html"

    def get(self, request):
        return render(request, self.template_name, {
            'form': UserProfileForm(instance=User.objects.get(pk=request.user.pk))
        })

    def post(self, request):
        form = UserProfileForm(request.POST, instance=User.objects.get(pk=request.user.pk))
        if form.is_valid() and form.has_changed():
            initial = User.objects.get(pk=request.user.pk)
            updated = form.save()

            leagues = get_objects_for_user(
                request.user,
                'league_member',
                klass=League.objects.all(),
                accept_global_perms=False)

            # Send notifications for all leagues that this user is a member of.
            for league in leagues:
                notify_admin_of_user_changes.delay(league, initial, updated)

            messages.info(request, "Updated profile saved. Thanks.")
            return HttpResponseRedirect(reverse("users:profile"))
        else:
            return render(request, self.template_name, {
                'form': form
            })
