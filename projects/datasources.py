import os
import requests
import json
import jsonlines
import random
import string
from pathlib import Path

from django.conf import settings


class AbsentSpecError(Exception):
    pass


class TextDatapoint:
    def __init__(self, text=None, meta=None):
        self.__text = text or []
        self.__meta = meta or []

    def add_datapoint(self, text, meta):
        self.__text.append(text.strip() if text else text)
        self.__meta.append(meta)

    def get_text(self, idx):
        return self.__text[idx]

    def get_meta(self, idx):
        return self.__meta[idx]

    def iterator(self):
        return zip(self.__text, self.__meta)


class AbstractDataSource:
    def __init__(self, spec_data):
        if type(spec_data) == str:
            self.__spec = json.loads(spec_data)
        elif type(spec_data) == dict:
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
        return ""

    def size(self):
        return self.__size

    def __getitem__(self, key):
        try:
            return self.__data[int(key)]
        except:
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


class TextFileSource(AbstractDataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._aux_keys = [('files',), ('folders',)]
        self.check_constraints()

        self.__mapping = []

        if self.get_spec('username'):
            self.__allowed_dirs = list(map(lambda x: x.format(username=self.get_spec('username')), settings.DATA_DIRS))
        else:
            fmt = string.Formatter()
            self.__allowed_dirs = [d for d in settings.DATA_DIRS if all([tup[1] is None for tup in fmt.parse(d)])]

        self.__files = []
        if self.get_spec('files'):
            for fname in self.get_spec('files'):
                found_file = None
                for d in self.__allowed_dirs:
                    cand_file = os.path.join(d, fname)
                    if os.path.exists(cand_file) and os.path.isfile(cand_file):
                        found_file = cand_file
                        break

                if found_file:
                    self.__files.append(found_file)

        if self.get_spec('folders'):
            for folder in self.get_spec('folders'):
                found_folder = None
                for d in self.__allowed_dirs:
                    cand_folder = os.path.join(d, folder)
                    if os.path.exists(cand_folder) and os.path.isdir(cand_folder):
                        found_folder = cand_folder
                        break

                if found_folder:
                    for d, subdirs, files in os.walk(found_folder):
                        for f in files:
                            self.__files.append(os.path.join(d, f))

        for fname in self.__files:
            found_file = None
            for d in self.__allowed_dirs:
                cand_file = os.path.join(d, fname)
                if os.path.exists(cand_file) and os.path.isfile(cand_file):
                    found_file = cand_file
                    break

            if found_file:
                # encoding to remove Byte Order Mark \ufeff (not sure if compatible with others)
                with open(found_file, encoding='utf-8-sig') as f:
                    self._add_datapoint(f.read())
                    self.__mapping.append(os.path.basename(fname))

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]

    def get_source_name(self, dp_id):
        # we know dp_id is for sure an integer
        return self.__mapping[int(dp_id)]


class JsonSource(AbstractDataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['key']
        self._aux_keys = [('files',), ('folders',)]
        self.check_constraints()

        self.__mapping = []

        if self.get_spec('username'):
            self.__allowed_dirs = map(lambda x: x.format(username=self.get_spec('username')), settings.DATA_DIRS)
        else:
            fmt = string.Formatter()
            self.__allowed_dirs = [d for d in settings.DATA_DIRS if all([tup[1] is None for tup in fmt.parse(d)])]

        self.__files = []
        if self.get_spec('files'):
            for fname in self.get_spec('files'):
                found_file = None
                for d in self.__allowed_dirs:
                    cand_file = os.path.join(d, fname)
                    if os.path.exists(cand_file) and os.path.isfile(cand_file):
                        found_file = cand_file
                        break

                if found_file:
                    self.__files.append(found_file)

        if self.get_spec('folders'):
            for folder in self.get_spec('folders'):
                found_folder = None
                for d in self.__allowed_dirs:
                    cand_folder = os.path.join(d, folder)
                    if os.path.exists(cand_folder) and os.path.isdir(cand_folder):
                        found_folder = cand_folder
                        break

                if found_folder:
                    self.__files.extend(Path(found_folder).rglob('*.json'))

        for fname in self.__files:
            d = json.load(open(fname))
            if type(d) == list:
                for el in d:
                    # this is all in-memory, of course
                    # TODO: think of fixing
                    self._add_datapoint(el[self.get_spec('key')])
            elif type(d) == dict:
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


class DialJSLSource(AbstractDataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['key']
        self._aux_keys = [('files',), ('folders',)]
        self.check_constraints()

        self.__mapping = []

        if self.get_spec('username'):
            self.__allowed_dirs = map(lambda x: x.format(username=self.get_spec('username')), settings.DATA_DIRS)
        else:
            fmt = string.Formatter()
            self.__allowed_dirs = [d for d in settings.DATA_DIRS if all([tup[1] is None for tup in fmt.parse(d)])]

        self.__files = []
        if self.get_spec('files'):
            for fname in self.get_spec('files'):
                found_file = None
                for d in self.__allowed_dirs:
                    cand_file = os.path.join(d, fname)
                    if os.path.exists(cand_file) and os.path.isfile(cand_file):
                        found_file = cand_file
                        break

                if found_file:
                    self.__files.append(found_file)

        if self.get_spec('folders'):
            for folder in self.get_spec('folders'):
                found_folder = None
                for d in self.__allowed_dirs:
                    cand_folder = os.path.join(d, folder)
                    if os.path.exists(cand_folder) and os.path.isdir(cand_folder):
                        found_folder = cand_folder
                        break

                if found_folder:
                    self.__files.extend(Path(found_folder).rglob('*.jsonl'))

        for fname in self.__files:
            dp = TextDatapoint()
            with jsonlines.open(fname) as reader:
                for d in reader:
                    try:
                        txt = d.pop(self.get_spec("key"))
                        dp.add_datapoint(txt, d)
                    except KeyError:
                        dp.add_datapoint(None, d)
            self._add_datapoint(dp)
            self.__mapping.append(os.path.basename(fname))

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]

    def get_source_name(self, dp_id):
        # we know dp_id is for sure an integer
        return self.__mapping[int(dp_id)]
