from django.db import models
from django.contrib.auth.models import User
from django.db.models import signals
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    language = models.CharField(_("language"), max_length=5, default='en')


def create_user_profile(sender, instance, created, **kwargs):
    """Create Profile for every new User."""
    if created:
        Profile.objects.create(user=instance)


signals.post_save.connect(create_user_profile, sender=User, weak=False,
                          dispatch_uid='models.create_user_profile')
