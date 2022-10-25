# -*- coding: utf-8 -*-
import os
import requests
import json
import jsonlines
import random
import string
import logging
from collections import defaultdict
from pathlib import Path

import magic

from django.conf import settings


logger = logging.getLogger(__name__)


class AbsentSpecError(Exception):
    pass


class AllowedDirsMixin:
    def __init__(self):
        self.__allowed_dirs = None

    def set_allowed_dirs(self, username):
        self.__allowed_dirs = None
        if username:
            self.__allowed_dirs = map(lambda x: x.format(username=username), settings.DATA_DIRS)
        else:
            fmt = string.Formatter()
            self.__allowed_dirs = [d for d in settings.DATA_DIRS if all([tup[1] is None for tup in fmt.parse(d)])]

    @property
    def allowed_dirs(self):
        return self.__allowed_dirs

    def find_folders(self, folders):
        found_folders = []
        for folder in folders:
            for d in self.__allowed_dirs:
                cand_folder = os.path.join(d, folder)
                if os.path.exists(cand_folder) and os.path.isdir(cand_folder):
                    found_folders.append(cand_folder)
                    break
        return sorted(found_folders)

    def find_files(self, files):
        found_files = []
        for fname in files:
            for d in self.__allowed_dirs:
                cand_file = os.path.join(d, fname)
                if os.path.exists(cand_file) and os.path.isfile(cand_file):
                    found_files.append(cand_file)
                    break
        return sorted(found_files)


class TextDatapoint:
    def __init__(self, text=None):
        self.__text = text or []

    def add_datapoint(self, text):
        self.__text.append(text.strip() if text else text)

    def get_text(self, idx):
        return self.__text[idx]


class AbstractDataSource:
    def __init__(self, spec_data):
        if isinstance(spec_data, str):
            self.__spec = json.loads(spec_data)
        elif isinstance(spec_data, dict):
            self.__spec = spec_data
        else:
            self.__spec = json.loads(str(spec_data))
        self.__data = []
        self.__size = 0

        self._required_keys = []
        self._aux_keys = []

    def check_constraints(self):
        absent = []
        for k in self._required_keys:
            if k not in self.__spec or not self.__spec[k]:
                absent.append(k)

        present_aux = any([set(key_set) & set(self.__spec.keys()) for key_set in self._aux_keys])

        if self._aux_keys and not present_aux:
            raise Warning("None of the auxiliary keys are present")

        if absent:
            raise AbsentSpecError("Required keys are missing: {}".format(", ".join(self._required_keys)))

    def get_spec(self, key):
        return self.__spec.get(key)

    def _add_datapoint(self, txt):
        self.__data.append(txt)
        self.__size += 1

    def data(self):
        return self.__data

    def get_random_datapoint(self):
        # return a tuple of (id, datapoint with this id)
        pass

    def get_source_name(self, dp_id):
        pass

    def size(self):
        return self.__size

    def __getitem__(self, key):
        try:
            return self.__data[int(key)]
        except (ValueError, IndexError) as e:
            logger.error(e)
            return None


class PlainTextSource(AbstractDataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)
        self._required_keys = ['texts']
        self.check_constraints()

        for text in self.get_spec('texts'):
            self._add_datapoint(text)

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]


class TextFileSource(AbstractDataSource, AllowedDirsMixin):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._aux_keys = [('files',), ('folders',)]
        self.check_constraints()

        self.__mapping = []

        self.set_allowed_dirs(self.get_spec('username'))
        self.__files = []
        if self.get_spec('files'):
            found_files = self.find_files(self.get_spec('files'))

            for found_file in found_files:
                self.__files.append(found_file)

        if self.get_spec('folders'):
            found_folders = self.find_folders(self.get_spec('folders'))

            for found_folder in found_folders:
                for d, _, files in os.walk(found_folder):
                    for f in sorted(files):
                        self.__files.append(os.path.join(d, f))

        for fname in self.__files:
            # encoding to remove Byte Order Mark \ufeff (not sure if compatible with others)
            with open(fname, encoding='utf-8-sig') as f:
                self._add_datapoint(f.read())
                self.__mapping.append(os.path.basename(fname))

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]

    def get_source_name(self, dp_id):
        # we know dp_id is for sure an integer
        return self.__mapping[int(dp_id)]


class JsonSource(AbstractDataSource, AllowedDirsMixin):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['key']
        self._aux_keys = [('files',), ('folders',)]
        self.check_constraints()

        self.__mapping = []

        self.set_allowed_dirs(self.get_spec('username'))
        self.__files = []
        if self.get_spec('files'):
            found_files = self.find_files(self.get_spec('files'))

            for found_file in found_files:
                self.__files.append(found_file)

        if self.get_spec('folders'):
            found_folders = self.find_folders(self.get_spec('folders'))

            for found_folder in found_folders:
                self.__files.extend(sorted(Path(found_folder).rglob('*.json')))

        for fname in self.__files:
            d = json.load(open(fname))
            if isinstance(d, list):
                for el in d:
                    # this is all in-memory, of course
                    # TODO: think of fixing
                    self._add_datapoint(el[self.get_spec('key')])
                    self.__mapping.append(os.path.basename(fname))
            elif isinstance(d, dict):
                self._add_datapoint(d[self.get_spec('key')])
                self.__mapping.append(os.path.basename(fname))

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]

    def get_source_name(self, dp_id):
        # we know dp_id is for sure an integer
        return self.__mapping[int(dp_id)]


class TextsAPISource(AbstractDataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)
        self.__endpoint = self.get_spec('endpoint').rstrip('/')

    def __getitem__(self, key):
        r = requests.get("{}/get_datapoint?key={}".format(self.__endpoint, key))
        if r.status_code == 200:
            data = r.json()
            return data['text']
        else:
            return ""

    def get_random_datapoint(self):
        r = requests.get("{}/get_random_datapoint".format(self.__endpoint))
        if r.status_code == 200:
            data = r.json()
            return data['key'], data['text']
        else:
            return -1, ""

    def size(self):
        r = requests.get("{}/size".format(self.__endpoint))
        if r.status_code == 200:
            data = r.json()
            return data['size']
        else:
            return 0

    def get_source_name(self, dp_id):
        r = requests.get("{}/get_source_name?key={}".format(self.__endpoint, key))
        if r.status_code == 200:
            data = r.json()
            return data['name']
        else:
            return ""
