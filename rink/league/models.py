from django.db import models


class Organization(models.Model):
    
    """
    Top level organization, can contain multiple leagues.
    """


    name = models.CharField(
        "Organization Name",
        max_length=50,
        help_text = "Example: 'Wreckers', 'Juniors', 'Madison Roller Derby', etc.",
    )

    slug = models.CharField(
        "Organization Slug",
        max_length=20,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class League(models.Model):
    """
    A leauge will contain a group of users and logically separate registration and billing
    events.
    """

    name = models.CharField(
        "Organization Name",
        max_length=50,
        help_text = "Example: 'Wreckers', 'Juniors', 'Madison Roller Derby', etc.",
    )

    slug = models.CharField(
        "Organization Slug",
        max_length=20,
        help_text = "Example: 'mrd', 'wreckers', 'juniors'. DO NOT CHANGE.",
    )

    organization = models.ForeignKey(
        'league.Organization',
        on_delete = models.CASCADE,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']