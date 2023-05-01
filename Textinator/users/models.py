# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.db.models import signals
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Profile(models.Model):
    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(_("preferred language"), max_length=10, default='en', choices=settings.LANGUAGES)
    fluent_in = models.TextField(_("fluent in"), default='en',
        help_text=_("Comma-separated list of language codes, compliant with RFC 5646"))
    enable_toolbox = models.BooleanField(_("enable toolbox?"), default=False)

    @property
    def fluent_languages(self):
        return self.fluent_in.split(",")



def create_user_profile(sender, instance, created, **kwargs):
    """Create Profile for every new User."""
    if created:
        Profile.objects.create(user=instance)


signals.post_save.connect(create_user_profile, sender=User, weak=False,
                          dispatch_uid='models.create_user_profile')
