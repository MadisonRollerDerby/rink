from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.contrib.auth.signals import user_logged_in
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from guardian.shortcuts import get_perms, get_perms_for_model


class RinkUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
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
        blank = True,
        default = 1,
    )

    league = models.ForeignKey(
        'league.League',
        "League",
        blank = True,
        default = 1,
    )

    derby_name = models.CharField(_('Derby Name'), blank=True, max_length=255)

    # Derby Name can be a maximum of 4 characters
    derby_number = models.CharField(_('Derby Number'), blank=True, max_length=4)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = RinkUserManager()

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
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'id': self.id})


def set_rink_session_data(sender, user, request, **kwargs):
    # Assist in figuring out which sections of the nav to show for admins
    # This pretty much just makes the permissions pretty and caches them for
    # future use.
    request.session['view_organization'] = user.organization.pk
    request.session['view_organization_slug'] = user.organization.slug
    request.session['view_league'] = user.league.pk
    request.session['view_league_slug'] = user.league.slug

    request.session['organization_permissions'] = get_perms(user, user.organization)
    request.session['league_permissions'] = get_perms(user, user.league)

    request.session['organization_admin'] = False
    request.session['league_admin'] = False

    if "org_admin" in request.session['organization_permissions']:
        # Org admin gets to be tagged as one here.
        request.session['organization_admin'] = True

    if request.session['organization_admin'] or "league_admin" in request.session['league_permissions']:
        # If we are an org or league admin, set all league permissions.
        request.session['league_admin'] = True
        request.session['league_permissions'] = []
        for perm in get_perms_for_model(user.league):
            request.session['league_permissions'].append(perm.codename)
            
# Attach the signal
user_logged_in.connect(set_rink_session_data)
