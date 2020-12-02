from django.db import models
from django.contrib.auth.models import User
from django.db.models import signals


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    language = models.CharField(max_length=5, default='en')


def create_user_profile(sender, instance, created, **kwargs):
    """Create Profile for every new User."""
    if created:
        Profile.objects.create(user=instance)


signals.post_save.connect(create_user_profile, sender=User, weak=False,
                          dispatch_uid='models.create_user_profile')
