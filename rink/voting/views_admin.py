from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View

from league.mixins import RinkLeagueAdminPermissionRequired

from .models import Election, ElectionQuestion, ElectionAnswer, VotingResponse, \
    VotingResponseAnswer, VotingInvite
from .forms import ElectionEmailInviteForm
from voting.tasks import send_voting_invite

from users.models import User


class VotingAdminView(RinkLeagueAdminPermissionRequired, View):
    election = None

    def dispatch(self, request, *args, **kwargs):
        # If slug isn't specified, that's fine, continue
        # If a slug is specified and not found it will return a 404

        # This needs to get locked down on a per-league basis
        try:
            self.election = get_object_or_404(Election, slug=kwargs['election_slug'])
            self.election_slug = self.election.slug
        except KeyError:
            pass

        self.request = request
        return super().dispatch(request, *args, **kwargs)

    def get_context(self):
        return {
            'election': self.election,
            'elections': Election.objects.filter(league=self.league),
            'election_selected': self.election,
        }

    def render(self, request, context={}):
        return render(request, self.template, {**context, **self.get_context()})


class AdminVotingElectionsList(VotingAdminView):
    # a list of elections
    template = 'voting/admin_elections_list.html'

    def get(self, request, *args, **kwargs):
        return self.render(request)


class AdminVotingStats(VotingAdminView):
    template = 'voting/admin_elections_stats.html'

    def get(self, request, *args, **kwargs):
        questions = ElectionQuestion.objects.filter(election=self.election).all().select_related()

        invites_sent = VotingInvite.objects.filter(election=self.election).all()
        invites_responded = VotingInvite.objects.filter(election=self.election, date_responded__isnull=False)
        invites_waiting = VotingInvite.objects.filter(election=self.election, date_responded__isnull=True)

        try:
            invites_responded_percent = int((float(invites_responded.count()) / invites_sent.count()) * 100)
        except ZeroDivisionError:
            invites_responded_percent = 0

        comments = VotingResponse.objects.filter(election=self.election).exclude(comment="").all()

        for question in questions:

            """
            Some questions don't have responses or votes, those won't show up in the aggregate functions.
            Manually smash the stats together with the list of votes/percent counts.
            """
            answers = []

            base_answers = ElectionAnswer.objects.filter(question=question).all()
            for answer in base_answers:
                answers.append({'answer': answer.answer, 'count': 0, 'percent': 0})

            """
            Now, check for fill-in answers. Add those to the answers dict.
            """
            responses = VotingResponseAnswer.objects.filter(question=question)
            for response in responses:
                for answer in answers:
                    if response.answer == answer["answer"]:
                        break
                else:
                    answers.append({'answer': response.answer, 'count': 0, 'percent': 0})

            answers_count = VotingResponseAnswer.objects.filter(question=question).values('answer').annotate(votes=Count('answer'))
            total_responses = responses.count()
            for answer_count in answers_count:
                try:
                    answer_count["percent"] = int((float(answer_count["votes"]) / total_responses) * 100)
                except ZeroDivisionError:
                    answer_count["percent"] = 0

                for stats_answer in answers:
                    if stats_answer["answer"] == answer_count["answer"]:
                        stats_answer["count"] = answer_count["votes"]
                        stats_answer["percent"] = answer_count["percent"]

            question.response_answers = answers

        return self.render(request, context={
            'questions': questions,
            'comments': comments,

            'invites_sent': invites_sent,
            'invites_responded': invites_responded,
            'invites_waiting': invites_waiting,
            'invites_responded_percent': invites_responded_percent,
        })


class AdminVotingInvites(VotingAdminView):
    template = 'voting/admin_elections_invites.html'

    def get(self, request, *args, **kwargs):
        return self.render(request, {
            'form': ElectionEmailInviteForm(league=self.league),
        })

    def post(self, request, *args, **kwargs):
        form = ElectionEmailInviteForm(league=self.league, data=request.POST)
        if form.is_valid():
            error = False
            emails = form.cleaned_data['emails'].splitlines()
            for email in emails:
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(request, "Invalid email: {}. Please check your list and try again.".format(email))
                    error = True

                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    messages.error(request, "Email address does not have a Rink account: {}".format(email))
                    error = True
                else:
                    if not user.has_perm('league_member', self.league):
                        messages.error(request, "Email {} does not appear to be a member of this league (no permissions).".format(email))
                        error = True

            if not error:
                invite_ids = []
                reminder_ids = []

                for email in emails:
                    user = User.objects.get(email=email)
                    try:
                        existing_invite = VotingInvite.objects.get(user=user, election=self.election)
                    except VotingInvite.DoesNotExist:
                        existing_invite = None

                    # If invite already exists for this email, just resend it
                    # and go onto the next email address.
                    if existing_invite and existing_invite.responded:
                        reminder_ids.append(existing_invite.pk)
                        continue

                    # I guess somehow we could not find the user here.
                    # This seems pretty inefficient, maybe someday find a better way to do this.
                    invite = VotingInvite.objects.create(
                        user=user,
                        election=self.election,
                    )

                    invite_ids.append(invite.pk)

                if len(invite_ids) > 0:
                    send_voting_invite.delay(invite_ids=invite_ids, reminder=False)
                    messages.success(request, 'Sending {} invites. They will be delivered shortly.'.format(len(invite_ids)))

                if len(reminder_ids) > 0:
                    send_voting_invite.delay(invite_ids=reminder_ids, reminder=True)
                    messages.success(request, 'Sending {} voting reminders. They will be delivered shortly.'.format(len(reminder_ids)))

                return HttpResponseRedirect(
                    reverse("voting:admin_voting_invites", kwargs={'election_slug': self.election.slug}))

        return self.render(request, {
            'form': ElectionEmailInviteForm(league=self.league),
        })
