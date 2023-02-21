# -*- coding: utf-8 -*-
import json
import copy
import operator

from django.db import models
from django.utils.translation import gettext_lazy as _


class DatapointInfo:
    def __init__(self, dp_id=None, text=None, ds=None, ds_def=None, proj_id=None, is_empty=False, no_data=False, is_dialogue=False, is_delayed=False, is_interactive=False):
        self.id = dp_id
        self.text = text if text is None else text.replace("\r\n", "\n")
        if ds:
            self.source_size = ds.size()
            self.source_name = ds.get_source_name(self.id)
        else:
            self.source_size, self.source_name = 0, ''

        if ds_def:
            self.source_id = ds_def.pk
            self.source_formatting = ds_def.formatting
        else:
            self.source_id, self.source_formatting = None, None

        self.source_spec = json.loads(ds_def.spec) if ds_def and ds_def.spec else None

        self.is_empty = is_empty
        self.no_data = no_data
        self.is_dialogue = is_dialogue
        self.project_id = proj_id
        self.is_delayed = is_delayed
        self.is_interactive = is_interactive

    def to_json(self):
        return {
            'id': self.id,
            'source_size': self.source_size,
            'source_name': self.source_name,
            'source_id': self.source_id,
            'source_formatting': self.source_formatting,
            'is_empty': self.is_empty,
            'project_id': self.project_id,
            'is_delayed': self.is_delayed,
            'is_interactive': self.is_interactive
        }


class JSONFormConfig:
    def __init__(self, json_cfg):
        self.__cfg = copy.deepcopy(json_cfg)
        if self.__cfg:
            self.__parse()

    def __parse(self):
        for tab in list(self.__cfg.keys()):
            if self.__cfg[tab]:
                tab_items = []
                for group_type, items in self.__cfg[tab].items():
                    for name, item in items.items():
                        tab_items.append(
                            [item.get("order"), group_type,
                             "{}_{}".format(tab, name), name, item["items"]])
                tab_items = [x[1:] for x in sorted(tab_items, key=operator.itemgetter(0))]

                self.__cfg[tab] = tab_items
            else:
                del self.__cfg[tab]

    @property
    def config(self):
        return self.__cfg


class Revisable(models.Model):
    revision_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='revisions')
    revision_changes = models.TextField(_("revision changes"), null=True, blank=True,
        help_text=_("The list of exact changes that were done to the object"))

    class Meta:
        abstract = True


class Orderable(models.Model):
    group_order = models.PositiveIntegerField(_("marker group order in the unit"), default=1,
        help_text=_("At the submission time"))

    class Meta:
        abstract = True
