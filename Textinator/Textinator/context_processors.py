# -*- coding: utf-8 -*-
from django.db.models import Q
from django.utils import timezone

from pinax.announcements.models import Announcement


def pinax_announcements(request):
    qs = Announcement.objects.filter(
        publish_start__lte=timezone.now()
    ).filter(
        Q(publish_end__isnull=True) | Q(publish_end__gt=timezone.now())
    ).filter(
        site_wide=True
    )

    exclusions = request.session.get("excluded_announcements", [])
    exclusions = set(exclusions)
    if request.user.is_authenticated:
        qs = qs.exclude(dismissals__user=request.user)
    else:
        qs = qs.exclude(members_only=True)
    return {
        "announcements": qs.exclude(pk__in=exclusions)
    }
