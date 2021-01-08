import os

from django.core.management.base import BaseCommand, CommandError
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
                MarkerAction.objects.get_or_create(name=p['name'], description=p['description'], file=p['file'])
                self.stdout.write(self.style.SUCCESS('Successfully registered plugin "%s"' % p['name']))
            except KeyError:
                continue