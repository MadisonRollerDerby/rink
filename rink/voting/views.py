from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View

from datetime import datetime

from voting.models import Election, VotingInvite, ElectionQuestion, \
    ElectionAnswer, VotingResponse, VotingResponseAnswer


class BallotThanks(View):
    def get(self, request, *args, **kwargs):
        election = get_object_or_404(
            Election,
            slug=kwargs['election_slug'],
            league__slug=kwargs['league_slug'],
        )

        return render(request, "voting/thanks.html", {
            'election': election,
            'league': election.league,
        })


class ViewBallot(View):
    election = None
    invite = None
    questions = None

    def dispatch(self, request, *args, **kwargs):
        error = False
        try:
            self.invite = VotingInvite.objects.get(uuid__exact=kwargs['vote_key'], election__league__slug=kwargs['league_slug'])
        except VotingInvite.DoesNotExist:
            error = "Survey not found."
        else:
            self.election = self.invite.election

            if self.invite.responded():
                error = "It appears you already voted in this election."
            elif self.election.start_date and self.election.start_date > timezone.now():
                error = "This election has not opened up for votes quite yet. Check back later."
            elif self.election.end_date < timezone.now():
                error = "This election has ended. Sorry."

        if error:
            return render(request, "voting/error.html", {
                "error": error,
                'league': self.election.league
            })

        self.questions = ElectionQuestion.objects.filter(election=self.election).select_related()

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, "voting/voting.html", {
            'election': self.election,
            'questions': self.questions,
            'league': self.election.league,
        })

    def post(self, request, *args, **kwargs):
        errors = False
        try:
            anything_else = request.POST.get("anything_else")
        except:
            anything_else = ""

        for question in self.questions:
            valid_answer = False
            answer_text = False
            custom_answer = ""
            try:
                answer_text = request.POST.get("question%s" % (question.id))
                valid_answer = ElectionAnswer.objects.get(question=question, answer=answer_text).answer
            except:
                pass

            if not valid_answer and answer_text == "custom" and question.allow_write_in:
                try:
                    custom_answer = request.POST.get("question%scustom" % (question.id))
                    if custom_answer != "":
                        valid_answer = "custom"
                except:
                    pass

            if valid_answer:
                question.selected = valid_answer
                question.custom = custom_answer
            else:
                question.error = "dammit"
                errors = True

        if not errors:
            """ Hooray, save the response. """
            """ At some point we would upgrade this to use legitimate database transactions, but for now
            we'll just keep it simple and not do that. """
            self.invite.date_responded = datetime.now()
            self.invite.save()

            response = VotingResponse()
            response.election = self.election
            response.comment = anything_else
            response.save()

            for question in self.questions:
                response_answer = VotingResponseAnswer()
                response_answer.response = response
                response_answer.question = question
                if question.selected == "custom":
                    response_answer.answer = question.custom
                else:
                    response_answer.answer = question.selected
                response_answer.save()

            return HttpResponseRedirect(reverse("voting:view_voting_thanks",
                    kwargs={'league_slug': self.election.league.slug,
                        'election_slug': self.election.slug,
            }))

        return render(request, "voting/voting.html", {
            'election': self.election,
            'questions': self.questions,
            'anything_else': anything_else,
            'errors': errors,
            'league': self.election.league,
        })
