# -*- coding: utf-8 -*-
import json
import copy
import operator

class DatapointInfo:
    def __init__(self, dp_id=None, text=None, ds=None, ds_def=None, proj_id=None, is_empty=False, no_data=False, is_dialogue=False, is_delayed=False):
        self.id = dp_id
        self.text = text
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

        self.source_spec = json.loads(ds_def.spec) if ds_def else None

        self.is_empty = is_empty
        self.no_data = no_data
        self.is_dialogue = is_dialogue
        self.project_id = proj_id
        self.is_delayed = is_delayed

    def to_json(self):
        return {
            'id': self.id,
            'source_size': self.source_size,
            'source_name': self.source_name,
            'source_id': self.source_id,
            'source_formatting': self.source_formatting,
            'is_empty': self.is_empty,
            'project_id': self.project_id,
            'is_delayed': self.is_delayed
        }


class JSONFormConfig:
    def __init__(self, json_cfg):
        self.__cfg = copy.deepcopy(json_cfg)
        if self.__cfg:
            self.__parse()

    def __parse(self):
        for tab in list(self.__cfg.keys()):
            if self.__cfg[tab]:
                groups = list(self.__cfg[tab].keys())
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
