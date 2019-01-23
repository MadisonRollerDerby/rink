from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse

from users.models import User

import uuid


class Election(models.Model):
    name = models.CharField(
        max_length=50,
        help_text="Name of this Election",
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    description = models.TextField(
        help_text="Description of this election to the members.",
    )

    slug = models.SlugField(blank=True)

    created_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Election Creation Date",
    )

    start_date = models.DateTimeField(
        help_text="Start date for this election",
    )

    end_date = models.DateTimeField(
        help_text="End date for this election",
    )

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('slug', 'league',)


class ElectionQuestion(models.Model):
    election = models.ForeignKey(
        'voting.Election',
        related_name="questions",
        on_delete=models.CASCADE,
    )

    question = models.TextField()

    allow_write_in = models.BooleanField(default=False)

    allow_comment = models.BooleanField(default=False)

    def __str__(self):
        return "%s | %s" % (self.election.name, self.question)


class ElectionAnswer(models.Model):
    question = models.ForeignKey(
        'voting.ElectionQuestion',
        related_name="answers",
        on_delete=models.CASCADE,
    )

    answer = models.TextField()

    def __str__(self):
        return "%s | %s - %s" % (
            self.question.election.name,
            self.question.question,
            self.answer[:50]
        )


class VotingInvite(models.Model):
    user = models.ForeignKey(
        User,
        related_name="voting_invite",
        on_delete=models.CASCADE,
    )

    election = models.ForeignKey(
        'voting.Election',
        related_name="voting_invite",
        on_delete=models.CASCADE,
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    date_sent = models.DateTimeField(auto_now_add=True)

    date_responded = models.DateTimeField(blank=True, null=True)

    def get_url(self):
        return reverse('voting:view_voting_invite', {
            'league_slug': self.election.league.slug,
            'vote_key': self.uuid,
        })

    def responded(self):
        if self.date_responded:
            return True
        return False

    def __str__(self):
        return "%s" % (self.user.email)

    class Meta:
        unique_together = ('user', 'election',)


class VotingResponse(models.Model):
    election = models.ForeignKey(
        'voting.Election',
        related_name="response",
        on_delete=models.CASCADE,
    )

    comment = models.TextField(blank=True)

    def __str__(self):
        return "Response to %s" % (self.election.name)


class VotingResponseAnswer(models.Model):
    response = models.ForeignKey(
        'voting.VotingResponse',
        related_name="response_answer",
        on_delete=models.CASCADE,
    )

    question = models.ForeignKey(
        'voting.ElectionQuestion',
        related_name="response_answer",
        on_delete=models.CASCADE,
    )

    answer = models.TextField(blank=True)

    def __str__(self):
        return "Answer: %s" % (self.answer)
