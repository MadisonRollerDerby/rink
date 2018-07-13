from django.contrib import messages
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from league.models import League
from registration.models import RegistrationData
from .forms import LegalDocumentAdminForm
from .models import LegalDocument, LegalSignature

# Publically accessable documents

class LegalDocumentPublicView(View):
    def get(self, request, document_slug, league_slug):
        return render(request, 'legal/public_document.html', {
            'document': get_object_or_404(
                LegalDocument,
                slug=document_slug,
                league=get_object_or_404(League, slug=league_slug),
            ),
        })         


# User Classes

class UserLegalSignaturesListView(ListView):
    def get(self, request):
        return render(request, 'legal/user_signed_forms.html', {
            'registration_data': RegistrationData.objects.filter(
                user=request.user,
                event__league=get_object_or_404(
                    League, 
                    pk=self.request.session['view_league']
                ),
            ).prefetch_related(
                'legalsignature_set',
                'event',
                'legalsignature_set__document',
            )
        })   


# Admin Stuff Below

class LegalDocumentList(ListView):
    model = LegalDocument
    template_name = 'legal/admin_document_list.html'

    def get_queryset(self):
        self.league = get_object_or_404(League, pk=self.request.session['view_league'])
        return LegalDocument.objects.filter(league=self.league).annotate(Count('legalsignature'))


class LegalDocumentAdminBaseView(View):
    def dispatch(self, request, *args, **kwargs):
        self.league = get_object_or_404(League, pk=request.session['view_league'])
        try:
            self.document = get_object_or_404(LegalDocument, pk=kwargs['document_id'], league=self.league)
            self.document.count = LegalSignature.objects.filter(document=self.document).count()
        except KeyError:
            self.document = None
        return super(LegalDocumentAdminBaseView, self).dispatch(request, *args, **kwargs)


class LegalDocumentCreateUpdate(LegalDocumentAdminBaseView):
    template_name = 'legal/admin_document_create_update.html'

    def render(self, request):
        return render(request, self.template_name, {
            'form': self.form,
            'document': self.document,
        }) 

    def get(self, request, *args, **kwargs):
        self.form = LegalDocumentAdminForm(instance=self.document)
        return self.render(request)

    def post(self, request, *args, **kwargs):
        self.form = LegalDocumentAdminForm(request.POST)
        if self.form.is_valid():
            try:
                self.document.pk
            except AttributeError:
                # new document
                self.document = self.form.save(commit=False)
                self.document.league = self.league
                self.document.save()
            else:
                # existing document
                self.document.name = self.form.cleaned_data['name']
                self.document.content = self.form.cleaned_data['content']
                self.document.date = self.form.cleaned_data['date']
                try:
                    self.document.save()
                except ValidationError:
                    messages.error(request, "You cannot edit this document. It has been agreed to by {} people.".format(self.document.count))
                    return self.render(request)

            messages.success(request, "{} ({}) legal document saved.".format(self.document.name, self.document.date))
            return HttpResponseRedirect(reverse('legal:admin_document_create_update', kwargs={'document_id':self.document.pk}))

        return self.render(request)


class LegalDocumentDelete(View):
    def get(self, request, document_id):
        league = get_object_or_404(League, pk=request.session['view_league'])
        document = get_object_or_404(LegalDocument, pk=document_id, league=league)
        document.delete()
        messages.success(request, "Document '{} ({}) deleted.".format(document.name, document.date))
        return HttpResponseRedirect(reverse('legal:admin_document_list'))


