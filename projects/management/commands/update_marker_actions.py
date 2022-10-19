# -*- coding: utf-8 -*-
import os

from django.core.management.base import BaseCommand
from django.contrib.staticfiles import finders
from projects.models import MarkerAction


class Command(BaseCommand):
    help = 'Updates the list of marker actions from the JS plugin folder'

    def handle(self, *args, **options):
        plugin_folder = finders.find('scripts/labeler_plugins')

        plugins = []
        for fname in os.listdir(plugin_folder):
            dct, inside_comment = {}, False
            dct["file"] = fname
            with open(os.path.join(plugin_folder, fname)) as f:
                for line in f:
                    if line.strip().startswith("/**"):
                        inside_comment = True
                    elif line.strip().startswith('*/'):
                        break
                    elif inside_comment:
                        k, v = line.replace('*', '').strip().split(':')
                        dct[k.strip()] = v.strip()
            plugins.append(dct)

        for p in plugins:
            try:
                m, _ = MarkerAction.objects.get_or_create(name=p['name'], file=p['file'])
                m.description = p['description']
                if 'admin_filter' in p:
                    m.admin_filter = p['admin_filter']
                m.save()
                self.stdout.write(self.style.SUCCESS('Successfully registered plugin "%s"' % p['name']))
            except KeyError:
                continue
