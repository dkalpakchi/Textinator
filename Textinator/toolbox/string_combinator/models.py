# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


# Create your models here.
class StringTransformationRule(models.Model):
    class Meta:
        verbose_name = _('string transformation rule')
        verbose_name_plural = _('string transformation rules')

    DELIMETER = "|"

    action = models.TextField(_("action"), help_text=_("Action"))
    s_from = models.TextField(_("from"),
        help_text=_("String to be transformed from"))
    s_to = models.TextField(_("to"),
        help_text=_("String(s) to be transformed into, separated by {}".format(DELIMETER)))
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("owner"))
    uuid = models.UUIDField()

    def to_json(self):
        return {
            'action': self.action,
            'from': self.s_from,
            'to': [x for x in self.s_to.split('|') if x],
            'uuid': str(self.uuid)
        }

    def __str__(self):
        return "{}: {} -> {}".format(self.action, self.s_from, self.s_to)


class StringTransformationSet(models.Model):
    class Meta:
        verbose_name = _('string transformation')
        verbose_name_plural = _('string transformations')

    data = models.JSONField()
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("owner"))
    batch = models.UUIDField()

    @property
    def title(self):
        return next(iter(self.data.keys()))


class FailedTransformation(models.Model):
    transformation = models.ForeignKey(StringTransformationSet, on_delete=models.SET_NULL, null=True, verbose_name=_("transformation"))
    value = models.TextField(_("value"), help_text=_("String to be filtered out"))

    def __str__(self):
        return self.value
