# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from projects.models import Context


class Command(BaseCommand):
    help = 'Remove Project-related objects not referenced by any other object (orphaned)'

    def handle(self, *args, **options):
        orphane_contexts = Context.objects.filter(
            input=None, label=None
        )

        orphane_contexts_cnt = orphane_contexts.count()

        if orphane_contexts_cnt > 0:
            orphane_contexts.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Removed {orphane_contexts_cnt} Context object(s)')
            )
        else:
            self.stdout.write("No orphaned Contexts found!")
