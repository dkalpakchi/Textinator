# -*- coding: utf-8 -*-
import os
import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group

from projects.models import (
    Marker, TaskTypeSpecification, Relation, MarkerPair, MarkerUnit
)


# python manage.py seed --mode=refresh

# Clear all data and creates addresses
MODE_REFRESH = 'refresh'

# Clear all data and do not create any object
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
    # if Marker.objects.count():
    #     logger.info("Markers have already been seeded")
    # else:
    logger.info("Creating markers for out-of-the-box annotation tasks")
    data = json.load(open(os.path.join(os.path.dirname(__file__), 'task_defaults.json')))

    created = 0
    marker_mapping = {}
    for spec in data['markers']:
        idx = spec['id']
        del spec['id']
        obj, is_created = Marker.objects.get_or_create(**spec)
        created += is_created
        marker_mapping[idx] = obj.pk
    logger.info("{} new markers are created.".format(created))

    created = 0
    relation_mapping = {}
    for spec in data['relations']:
        idx = spec['id']
        pairs = spec['pairs']
        del spec['id']
        del spec['pairs']
        obj, is_created = Relation.objects.get_or_create(**spec)
        created += is_created
        relation_mapping[idx] = obj.pk

        for first, second in pairs:
            mp, _ = MarkerPair.objects.get_or_create(
                first_id=marker_mapping[first],
                second_id=marker_mapping[second]
            )
            obj.pairs.add(mp)
            obj.save()
    logger.info("{} new relations are created.".format(created))

    created = 0
    unit_mapping = {}
    for spec in data['units']:
        idx = spec['id']
        del spec['id']
        obj, is_created = MarkerUnit.objects.get_or_create(**spec)
        created += is_created
        unit_mapping[idx] = obj.pk
    logger.info("{} new marker units are created.".format(created))

    created = 0
    for task_type, spec in data['specs'].items():
        for x in spec["markers"]:
            x["id"] = marker_mapping[x["id"]]
            if "unit_id" in x:
                x["unit_id"] = unit_mapping[x["unit_id"]]

        if spec.get('relations'):
            spec['relations'] = [relation_mapping[x] for x in spec['relations']]

        if spec.get("actions"):
            for x in spec["actions"]:
                x["marker_id"] = marker_mapping[x["marker_id"]]

        obj, is_created = TaskTypeSpecification.objects.get_or_create(
            task_type=task_type,
            config=spec
        )
        created += is_created
    logger.info("{} new specifications are created.".format(created))

    created = 0
    group_permissions = {
        'project_managers': [
            'add_project', 'view_project', 'change_project',
            'add_marker', 'view_marker',
            'add_relation', 'view_relation',
            'add_datasource', 'change_datasource', 'view_datasource',
            'add_markerunit', 'change_markerunit', 'view_markerunit',
            'add_markerpair', 'change_markerpair', 'view_markerpair',
            'add_markercontextmenuitem', 'change_markercontextmenuitem', 'delete_markercontextmenuitem', 'view_markercontextmenuitem',
            'add_markerrestriction', 'change_markerrestriction', 'delete_markerrestriction', 'view_markerrestriction',
            'add_markervariant', 'change_markervariant', 'delete_markervariant', 'view_markervariant',
            'add_relationvariant', 'change_relationvariant', 'delete_relationvariant', 'view_relationvariant',
            'add_premarker', 'change_premarker', 'delete_premarker', 'view_premarker',
        ],
        'user_manager': [
            'add_user', 'change_user', 'view_user'
        ],
        'file_managers': [
            'view_filebrowser'
        ],
        'evaluation_managers': [
            'scientific_survey.add_answer', 'scientific_survey.view_answer', 'scientific_survey.change_answer',
            'scientific_survey.add_answergroup', 'scientific_survey.view_answergroup', 'scientific_survey.change_answergroup',
            'scientific_survey.add_category', 'scientific_survey.change_category', 'scientific_survey.view_category',
            'scientific_survey.add_question', 'scientific_survey.change_question', 'scientific_survey.view_question',
            'scientific_survey.add_survey', 'scientific_survey.change_survey', 'scientific_survey.view_survey',
            'scientific_survey.add_response', 'scientific_survey.change_response', 'scientific_survey.view_response'
        ]
    }

    for x in group_permissions:
        g, is_created = Group.objects.get_or_create(name=x)
        created += is_created
        if is_created > 0:
            for perm in group_permissions[x]:
                try:
                    if '.' in perm:
                        app_label, codename = perm.split('.')
                        g.permissions.add(Permission.objects.get(codename=codename, content_type__app_label=app_label))
                    else:
                        g.permissions.add(Permission.objects.get(codename=perm))
                except Permission.DoesNotExist:
                    print("{} does not exist".format(perm))
                    continue

    g, is_created = Group.objects.get_or_create(name="translators")
    for x in ["translators-{}".format(l) for l, _ in settings.LANGUAGES]:
        g, is_created = Group.objects.get_or_create(name=x)
        created += is_created

    logger.info("{} new user groups are created.".format(created))


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
