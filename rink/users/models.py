from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.contrib.auth.signals import user_logged_in
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from markdownx.utils import markdownify

from league.models import League

from guardian.shortcuts import (
    assign_perm, get_perms, get_perms_for_model, get_objects_for_user)


class RinkUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('Invalid email address, please try again.')

        user = self.model(
            email=self.normalize_email(email),
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):

    first_name = models.CharField(_('First Name'), blank=True, max_length=255)
    last_name = models.CharField(_('Last Name'), blank=True, max_length=255)

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )

    organization = models.ForeignKey(
        'league.Organization',
        "Organization",
        blank=True,
        null=True,
    )

    league = models.ForeignKey(
        'league.League',
        "League",
        blank=True,
        null=True,
    )

    derby_name = models.CharField(_('Derby Name'), blank=True, max_length=255)

    # Derby Name can be a maximum of 4 characters
    derby_number = models.CharField(_('Derby Number'), blank=True, max_length=50)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    tags = models.ManyToManyField(
        'users.Tag',
        through='UserTag',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = RinkUserManager()

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        if self.first_name and self.last_name:
            name = "{} {}".format(self.first_name, self.last_name)
        elif self.last_name:
            name = self.last_name
        elif self.first_name:
            name = self.first_name
        else:
            name = self.email

        if self.derby_name:
            name = "{} ({})".format(name, self.derby_name)

        return name

    @property
    def legal_name(self):
        if not self.first_name and not self.last_name:
            return ""
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    """
    def set_default_perms(self):
        # If league or organization is set and somehow we are out of sync
        # add this user to the correct permissions
        if self.is_admin and self.organization:
            assign_perm("org_admin", self.organization)
        elif self.league:
            assign_perm("league_member", self.league)
    """

    """
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True
    """


class Tag(models.Model):
    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    text = models.CharField(
        "Tag Text",
        max_length=50,
    )

    color = models.CharField(
        "Tag Color",
        max_length=50,
        blank=True,
    )

    def __str__(self):
        return self.text

    class Meta:
        unique_together = ['league', 'text']
        ordering = ['league', 'text']


class UserTag(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    tag = models.ForeignKey(
        'users.Tag',
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ['user', 'tag']


LOG_MESSAGE_TYPE_CHOICES = [
    # rink code // bootstrap alert class
    ('default', 'info'),

    ('primary', 'primary'),
    ('secondary', 'secondary'),
    ('info', 'info'),
    ('light', 'light'),
    ('dark', 'dark'),

    ('success', 'success'),
    ('green', 'success'),

    ('warning', 'warning'),
    ('yellow', 'warning'),

    ('danger', 'danger'),
    ('red', 'danger'),
    ('error', 'danger'),
]


class UserLog(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    league = models.ForeignKey(
        'league.League',
        on_delete=models.CASCADE,
    )

    message = models.TextField(
        "User Note",
        help_text="Some notes or messages to keep on hand for this user. These notes are NOT viewable by the user."
    )

    group = models.CharField(
        "Message Group",
        max_length=50,
        default='note',
    )

    message_type = models.CharField(
        "Message Type",
        max_length=50,
        choices=LOG_MESSAGE_TYPE_CHOICES,
        default="default",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    admin_user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_user",
    )

    date = models.DateTimeField(
        auto_now_add=True,
    )

    @property
    def message_html(self):
        return markdownify(self.message)

    def __str__(self):
        return "{} - {} - {} - {}".format(self.league, self.user, self.message_type, self.message[:75])

    class Meta:
        ordering = ['-date']


def set_rink_session_data(sender, user, request, **kwargs):
    # Assist in figuring out which sections of the nav to show for admins
    # This pretty much just makes the permissions pretty and caches them for
    # future use.

    try:
        view_league = kwargs.get('league', user.league)
    except AttributeError:
        raise PermissionDenied("You do not appear to have access to this league. Please contact your league admin for assistance. Sorry.")

    view_organization = view_league.organization

    user_member_leagues = get_objects_for_user(user, 'league_member', League)
    #if view_league not in user_member_leagues:
    #    raise PermissionDenied("You do not appear to have access to this league. Please contact your league admin for assistance. Sorry.")

    # Organization
    request.session['view_organization'] = view_organization.pk
    request.session['view_organization_slug'] = view_organization.slug
    request.session['organization_permissions'] = get_perms(user, view_organization)

    # League
    request.session['view_league'] = view_league.pk
    request.session['view_league_slug'] = view_league.slug
    request.session['league_permissions'] = get_perms(user, view_league)

    # Is user an admin?
    request.session['organization_admin'] = False
    request.session['league_admin'] = False

    # League switcher menu cache
    request.session['league_switcher_menu'] = []
    for league in user_member_leagues:
        if league != view_league:
            request.session['league_switcher_menu'].append(
                [league.pk, league.slug, league.name]
            )

    if "org_admin" in request.session['organization_permissions']:
        # Org admin gets to be tagged as one here.
        request.session['organization_admin'] = True

    if request.session['organization_admin'] or "league_admin" in request.session['league_permissions']:
        # If we are an org or league admin, set all league permissions.
        request.session['league_admin'] = True
        request.session['league_permissions'] = []
        if user.league:
            for perm in get_perms_for_model(view_league):
                request.session['league_permissions'].append(perm.codename)


# Attach the signal
user_logged_in.connect(set_rink_session_data)
