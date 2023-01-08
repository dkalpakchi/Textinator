# -*- coding: utf-8 -*-
import re
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import F, Func

from projects.models import Context, Project, Label, Input, DataSource


class Command(BaseCommand):
    help = 'Recover datasource and datapoints to Contexts from access logs'

    def add_arguments(self, parser):
        parser.add_argument('project', type=int, help="Project ID")

    def handle(self, *args, **options):
        project = Project.objects.get(pk=options['project'])
        datasources = project.datasources.all()
        ds_inst = [d._load() for d in datasources]
        sizes = [d.size() for d in ds_inst]
        labels = Label.objects.filter(marker__project=project, context__datapoint__isnull=True)
        inputs = Input.objects.filter(marker__project=project, context__datapoint__isnull=True)

        html_tags_re = re.compile('<.*?>')
        space_re = re.compile("\s")
        punct_digits_re = re.compile("[{}{}]".format(string.punctuation, string.digits))

        def clean(t):
            t = t.replace("&nbsp;", "").replace("#", "").replace("\r", "").replace('”', '')
            t = re.sub(html_tags_re, "", t)
            t = re.sub(space_re, "", t)
            t = re.sub(punct_digits_re, "", t)
            return t

        object_groups = [labels, inputs]

        for objects in object_groups:
            if objects.count() > 0:
                cnt = 0
                for obj in objects:
                    found = False
                    content = clean(obj.context.content)
                    for ds_id, ds in enumerate(ds_inst):
                        for dp_id in range(sizes[ds_id]):
                            text = clean(ds[dp_id])

                            if content in text or content == text:
                                found = True
                                cnt += 1
                                obj.context.datasource = datasources[ds_id]
                                obj.context.datapoint = dp_id
                                obj.context.save()
                                break
                        if found:
                            break

                    if not found:
                        print(content)
                        print()

                print("{} of {} contexts fixed".format(cnt, objects.count()))
