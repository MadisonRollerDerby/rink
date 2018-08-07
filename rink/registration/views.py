from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from guardian.shortcuts import assign_perm
from guardian.mixins import LoginRequiredMixin
import re

from .forms import RegistrationSignupForm, RegistrationDataForm, LegalDocumentAgreeForm
from .models import RegistrationEvent, RegistrationInvite, RegistrationData
from billing.models import (
    BillingPeriod, BillingGroup, BillingPeriodCustomPaymentAmount,
    UserStripeCard, Invoice)
from legal.models import LegalDocument, LegalSignature

from registration.tasks import send_registration_confirmation


def registration_error(request, event, error_code):
    return render(request, 'registration/register_error.html', {
        'event': event,
        'error_code': error_code,
    })


class RegistrationView(View):
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(RegistrationEvent, slug=kwargs['event_slug'])
        return super(RegistrationView, self).dispatch(request, *args, **kwargs)


class RegisterBegin(RegistrationView):
    def get(self, request, event_slug, invite_key=None):
        invite = None

        if invite_key:
            invite = get_object_or_404(RegistrationInvite, uuid=invite_key)

            if self.event.invite_expiration_date and self.event.invite_expiration_date < timezone.now():
                # Invites no longer work after this date.
                return registration_error(request, self.event, "registration_closed")

            if invite.user:
                # User attached to this invite, require login

                if not request.user.is_authenticated:
                    messages.info(request, "Please login to register for '{}'".format(self.event.name))
                    return redirect('{}?next={}'.format(reverse('account_login'), request.path))

                if invite.user != request.user:
                    # Different user is attached to this invite compared to whom is logged in
                    return registration_error(request, self.event, "user_conflict")
        else:
            # Check if event is available to be registered by the public
            if self.event.public_registration_open_date and self.event.public_registration_open_date > timezone.now():
                return registration_error(request, self.event, "registration_not_yet_open")

            if self.event.public_registration_closes_date and self.event.public_registration_closes_date < timezone.now():
                return registration_error(request, self.event, "registration_closed")

        request.session['register_event_id'] = self.event.pk
        if invite:
            request.session['register_invite_id'] = invite.pk

        if request.user.is_authenticated:
            # If logged in, go to the registration form
            return HttpResponseRedirect(reverse("register:show_form", kwargs={'event_slug': self.event.slug}))
        else:
            # If not logged in, user needs to create an account
            messages.info(request, "Please create an account to register for '{}'".format(self.event.name))
            return HttpResponseRedirect(reverse("register:create_account", kwargs={'event_slug': self.event.slug}))


class RegisterCreateAccount(RegistrationView):
    template = 'registration/register_create_account.html'

    def get(self, request, event_slug):
        form = RegistrationSignupForm()
        return render(request, self.template, {'form': form, 'event': self.event})

    def post(self, request, event_slug):
        form = RegistrationSignupForm(request.POST)
        if form.is_valid():
            user = form.save(league=self.event.league)
            auth_user = authenticate(request, username=user.email, password=form.cleaned_data['password1'])
            login(request, auth_user)

            # Update user associated with this invite, if there is one.
            # This way the user will be forced to sign back in and use this email
            # address, as the account already exists now with this email address.
            # May cause some confusion if the process stops somewhere, but I guess
            # people will be more confused if we just have users and invites
            # floating about.
            try:
                invite = RegistrationInvite.objects.get(pk=request.session['register_invite_id'])
            except KeyError:
                pass
            except RegistrationInvite.DoesNotExist:
                # huh. okay.
                pass
            else:
                invite.user = user
                invite.save()

            return HttpResponseRedirect(reverse("register:show_form", kwargs={'event_slug': self.event.slug}))

        return render(request, self.template, {'form': form, 'event': self.event})


class RegisterShowForm(LoginRequiredMixin, RegistrationView):
    template = 'registration/register_form.html'

    def get_billing_period(self):
        billing_period = None

        # If we are inside a billing period already, use that one to register
        billing_period_query = BillingPeriod.objects.filter(
            event=self.event,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
        )
        if billing_period_query.count() != 1:
            # If we are registering early, use the first period available
            billing_period_query = BillingPeriod.objects.filter(
                event=self.event,
                start_date__gte=timezone.now(),
            ).all()[:1]
        if billing_period_query.count() == 1:
            billing_period = billing_period_query.get()
        return billing_period

    def get_invite_billing_group(self, request):
        try:
            if request.session.get('register_invite_id', None):
                invite = RegistrationInvite.objects.get(pk=request.session['register_invite_id'])
        except RegistrationInvite.DoesNotExist:
            return None
        else:
            return invite.billing_group

    def get(self, request, event_slug):

        # Check if the user has already registered
        try:
            data = RegistrationData.objects.get(user=request.user, event=self.event)
        except RegistrationData.DoesNotExist:
            pass
        else:
            return registration_error(request, self.event, "already_registered")

        # Check if user has some registration data we can already use
        try:
            existing_registration = RegistrationData.objects.filter(
                user=request.user,
                organization=self.event.league.organization,
            ).order_by('-registration_date').get()
        except RegistrationData.DoesNotExist:
            existing_registration = None

        if existing_registration:
            existing_registration.id = None
            existing_registration.invite = None
            existing_registration.event = None
            existing_registration.registration_date = None
            existing_registration.email = request.user.email

            form = RegistrationDataForm(
                logged_in_user_id=request.user.pk, instance=existing_registration)
        else:
            form = RegistrationDataForm(
                logged_in_user_id=request.user.pk,
                initial={
                    'contact_email': request.user.email,
                    'contact_state': self.event.league.default_address_state,
                    'derby_insurance_type': self.event.league.default_insurance_type,
                })

        # Legal documents that need to be agreed to
        if self.event.legal_forms.count() > 0:
            legal_form = LegalDocumentAgreeForm(event=self.event)
        else:
            legal_form = None

        # Get Billing Period
        num_billing_periods = BillingPeriod.objects.filter(event=self.event).count()
        billing_period = self.get_billing_period()
        billing_amount = billing_period.get_invoice_amount(self.get_invite_billing_group(request))

        #  If there are no billing periods available... I guess don't include it.
        return render(request, self.template, {
            'form': form,
            'legal_form': legal_form,
            'event': self.event,
            'billing_period': billing_period,
            'billing_amount': billing_amount,
            'num_billing_periods': num_billing_periods,
        })

    def post(self, request, event_slug):
        form = RegistrationDataForm(logged_in_user_id=request.user.pk, data=request.POST)
        legal_form = LegalDocumentAgreeForm(event=self.event, data=request.POST)

        if form.is_valid() and legal_form.is_valid():

            #num_billing_periods = BillingPeriod.objects.filter(event=self.event).count()
            billing_period = self.get_billing_period()
            billing_amount = billing_period.get_invoice_amount(self.get_invite_billing_group(request))
            invoice_description = billing_period.get_invoice_description()

            # Create an invoice for this billing period
            invoice, created = Invoice.objects.get_or_create(
                user=request.user,
                league=self.event.league,
                billing_period=billing_period,
                defaults={
                    'invoice_amount': billing_amount,
                    'invoice_date': timezone.now(),
                    'autopay_disabled': True,
                    'description': invoice_description,
                }
            )

            card_profile, created = UserStripeCard.objects.get_or_create(
                user=request.user,
                league=self.event.league,
            )
            try:
                card_profile.update_from_token(form.cleaned_data['stripe_token'])
                card_profile.charge(invoice=invoice, send_receipt=False)
            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.error(request, "<p>We were unable to charge your credit card.</p>\
                    <p>Reason: {}</p>\
                    <p>Please try again or contact us if you continue to have issues.</p>".format(
                    err.get('message'))
                )
            except Exception as e:
                body = e.json_body
                err = body.get('error', {})
                messages.error(request, "<p>Generic Error. Weird. We were unable to charge your credit card.</p>\
                    <p>Reason: {}</p>\
                    <p>Please try again or contact us if you continue to have issues.</p>".format(
                    err.get('message'))
                )
            else:
                # Card successfully saved.
                # Save registration data.
                registration_data = form.save(commit=False)
                registration_data.user = request.user
                registration_data.event = self.event
                registration_data.league = self.event.league
                registration_data.organization = self.event.league.organization

                try:
                    if request.session.get('register_invite_id', None):
                        registration_data.invite = RegistrationInvite.objects.get(
                            pk=request.session['register_invite_id'])
                except RegistrationInvite.DoesNotExist:
                    pass

                registration_data.save()
                # Save details to user profile
                user = request.user
                user.first_name = registration_data.contact_first_name
                user.last_name = registration_data.contact_last_name
                user.email = registration_data.contact_email
                user.derby_name = registration_data.derby_name
                user.derby_number = registration_data.derby_number
                user.save()

                # Update permissions
                assign_perm("league_member", user, self.event.league)

                # Save legal signatures
                # This should already be validated in the dynamic form model
                regex = re.compile('^Legal(\d+)$')
                for field in legal_form.fields:
                    match = regex.match(str(field))
                    if match:
                        LegalSignature.objects.create(
                            user=user,
                            document=LegalDocument.objects.get(pk=match.group(1)),
                            league=self.event.league,
                            event=self.event,
                            registration=registration_data,
                        )
                    # else:
                    #   I suppose the document could go away or not be found?
                    #    But probably not likely...

                completed_time = timezone.now()

                # Save registration invite
                if registration_data.invite:
                    registration_data.invite.completed_date = completed_time
                    registration_data.invite.save()
                else:
                    # Create the registration invite if it was a public invite
                    registration_data.invite = RegistrationInvite.objects.create(
                        user=user,
                        sent_date=completed_time,
                        completed_date=completed_time,
                        public_registration=True,
                        email=user.email,
                        event=self.event,
                    )

                # Send email confirmation of registration
                print("sending...")
                #from pudb import set_trace; set_trace()
                from rink.taskapp.celery import debug_task
                debug_task.delay()
                send_registration_confirmation.delay(registration_data.pk)
                print("sent.")

                # Reset session data
                if request.session.get('register_invite_id', None):
                    del request.session['register_invite_id']
                    request.session.modified = True
                if request.session.get('register_event_id', None):
                    del request.session['register_event_id']
                    request.session.modified = True

                return HttpResponseRedirect(reverse("register:done", kwargs={'event_slug': self.event.slug}))

        #  If there are any errors with the email address field show this message
        #   if its a duplicate email address.
        if not form.is_valid() and form.errors.get('contact_email', None):
            if form.errors['contact_email'].as_data()[0].code == "username_conflict":
                messages.error(request, "<h4>Duplicate Email Address</h4> \
                    <p>An account already exists with that email address.</p> \
                    <p>You can use attempt to \
                    <a href='{}'>login to that account</a>, \
                    <a href='{}'>reset the password</a>, \
                    or use a different email address.</p>".format(
                        reverse('account_logout'),
                        reverse('account_reset_password'),
                ))

        return render(
            request,
            self.template,
            {'form': form, 'legal_form': legal_form, 'event': self.event}
        )


class RegisterDone(LoginRequiredMixin, RegistrationView):
    template = 'registration/register_done.html'

    def get(self, request, event_slug):
        return render(request, self.template, {'event': self.event})
