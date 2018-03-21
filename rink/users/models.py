from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


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




class User(AbstractBaseUser):

    first_name = models.CharField(_('First Name'), blank=True, max_length=255)
    last_name = models.CharField(_('Last Name'), blank=True, max_length=255)

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
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
