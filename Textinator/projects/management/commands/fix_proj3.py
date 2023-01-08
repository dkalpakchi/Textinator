# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.db.models import F, Func

from projects.models import Project, Input, Batch, Label, Marker, MarkerVariant


class Command(BaseCommand):
    help = 'Recover datasource and datapoints to Contexts from access logs'

    def handle(self, *args, **options):
        batch_ids = Label.objects.filter(marker__project_id=3).values_list('batch_id', flat=True)
        batches = Batch.objects.filter(pk__in=batch_ids)
        marker = Marker.objects.filter(name="Question").first()
        mv, _ = MarkerVariant.objects.get_or_create(marker=marker, project_id=3)

        for batch in batches:
            for inp in batch.input_set.all():
                inp.marker = mv
                inp.save()
