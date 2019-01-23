from voting.models import Election, ElectionQuestion, ElectionAnswer, \
    VotingInvite, VotingResponse, VotingResponseAnswer
from django.contrib import admin

admin.site.register(Election)
admin.site.register(ElectionQuestion)
admin.site.register(ElectionAnswer)
admin.site.register(VotingInvite)
admin.site.register(VotingResponse)
admin.site.register(VotingResponseAnswer)
