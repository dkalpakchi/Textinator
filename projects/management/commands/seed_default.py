import os
import json
import logging
import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group

from projects.models import Marker, TaskTypeSpecification


# python manage.py seed --mode=refresh

""" Clear all data and creates addresses """
MODE_REFRESH = 'refresh'

""" Clear all data and do not create any object """
MODE_CLEAR = 'clear'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Command(BaseCommand):
    help = "seed database for testing and development."

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str, default=MODE_REFRESH, help="Mode")

    def handle(self, *args, **options):
        self.stdout.write('seeding data...')
        run_seed(self, options['mode'])
        self.stdout.write('done.')


def clear_data():
    """Deletes all the table data"""
    logger.info("Delete Marker instances")
    Marker.objects.all().delete()


def create_data():
    if Marker.objects.count():
        logger.info("Markers have already been seeded")
    else:
        logger.info("Creating markers for out-of-the-box annotation tasks")
        data = json.load(open(os.path.join(os.path.dirname(__file__), 'defaults.json')))
        
        created = 0
        marker_mapping = {}
        for spec in data['markers']:
            idx = spec['id']
            del spec['id']
            obj, is_created = Marker.objects.get_or_create(**spec)
            created += is_created
            marker_mapping[idx] = obj.code
        logger.info("{} markers are created.".format(created))

        created = 0
        for task_type, spec in data['specs'].items():
            for x in spec["markers"]:
                x["id"] = marker_mapping[x["id"]]

            obj, is_created = TaskTypeSpecification.objects.get_or_create(
                task_type=task_type, 
                config=spec
            )
            created += is_created
        logger.info("{} specifications are created.".format(created))

        created = 0
        group_permissions = {
            'project_managers': [
                'add_project', 'view_project', 'change_project',
                'add_marker', 'view_marker',
                'add_relation', 'view_relation',
                'add_datasource', 'change_datasource', 'delete_datasource', 'view_datasource',
                'add_markerrestriction', 'change_markerrestriction', 'delete_markerrestriction', 'view_markerrestriction',
                'add_markerunit', 'change_markerunit', 'delete_markerunit', 'view_markerunit',
                'add_markervariant', 'change_markervariant', 'delete_markervariant', 'view_markervariant',
                'add_relationvariant', 'change_relationvariant', 'delete_relationvariant', 'view_relationvariant',
                'add_premarker', 'change_premarker', 'delete_premarker', 'view_premarker'
            ],
            'user_manager': [
                'add_user', 'change_user', 'view_user'
            ]
        }

        for x in ["translators", "user_managers", "project_managers"]:
            g, is_created = Group.objects.get_or_create(name=x)
            created += is_created
            if is_created > 0:
                for perm in group_permissions.get(x, []):
                    g.permissions.add(Permission.objects.get(codename=perm))

        for x in ["translators-{}".format(l) for l, _ in settings.LANGUAGES]:
            g, is_created = Group.objects.get_or_create(name=x)
            created += is_created

        logger.info("{} user groups are created.".format(created))


def run_seed(self, mode):
    """ Seed database based on mode

    :param mode: refresh / clear 
    :return:
    """
    # Clear data from tables
    if mode == MODE_CLEAR:
        clear_data()
        return

    create_data()
