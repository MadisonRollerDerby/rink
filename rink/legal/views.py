from django.shortcuts import render, get_object_or_404
from django.views import View

from league.models import League
from .models import LegalDocument, LegalSignature


class LegalDocumentPublicView(View):
    def get(self, request, document_slug, league_slug):
        return render(request, 'legal/public_document.html', {
                'document': get_object_or_404(
                    LegalDocument,
                    slug=document_slug,
                    league=get_object_or_404(League, slug=league_slug),
                ),
        })         



class UserLegalSignaturesListView(View):
    pass


# admin to add/edit/delete/list