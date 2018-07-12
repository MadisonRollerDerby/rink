from django.contrib import admin
from .models import LegalDocument, LegalSignature

admin.site.register(LegalDocument)
admin.site.register(LegalSignature)