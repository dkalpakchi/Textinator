import os
import requests
import glob
import json
import random

class AbsentSpecError(Exception):
    pass


class DataSource:
    def __init__(self, spec_data):
        self.__spec = json.loads(spec_data)
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

    def size(self):
        return self.__size

    def __getitem__(self, key):
        try:
            return self.__data[int(key)]
        except:
            return None


class PlainTextSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)
        self._required_keys = ['texts']
        self.check_constraints()

        for text in self.get_spec('texts'):
            self._add_datapoint(text)

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]


class TextFileSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._aux_keys = [('files',), ('folders',), ('remote',)]
        self.check_constraints()

        self.mapping = []

        self.__files = []
        if self.get_spec('files'):
            self.__files.extend(self.get_spec('files'))

        if self.get_spec('folders'):
            for folder in self.get_spec('folders'):
                for d, subdirs, files in os.walk(folder):
                    for f in files:
                        self.__files.append(os.path.join(d, f))

        for fname in self.__files:
            # encoding to remove Byte Order Mark \ufeff (not sure if compatible with others)
            with open(fname, encoding='utf-8-sig') as f:
                self._add_datapoint(f.read())
                self.mapping.append(os.path.basename(fname))

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]


class JsonSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['key']
        self._aux_keys = [('files',), ('folders',), ('remote',)]
        self.check_constraints()

        self.__files = []
        if self.get_spec('files'):
            self.__files.extend(self.get_spec('files'))

        if self.get_spec('folders'):
            for folder in self.get_spec('folders'):
                self.__files.extend(glob.glob(os.path.join(folder, '*.json')))

        if self.get_spec('remote'):
            # TODO: fix
            for url in self.get_spec('remote'):
                res = requests.get(url, allow_redirects=True)
                content_type = res.headers.get('content-type')

        for fname in self.__files:
            d = json.load(open(fname))
            if type(d) == list:
                for el in d:
                    # this is all in-memory, of course
                    # TODO: think of fixing
                    self._add_datapoint(el[self.get_spec('key')])
            elif type(d) == dict:
                self._add_datapoint(d[self.get_spec('key')])

    def get_random_datapoint(self):
        idx = random.randint(0, self.size() - 1)
        return idx, self[idx]


class TextsAPISource(DataSource):
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
            return data['id'], data['text']
        else:
            return -1, ""

    def size(self):
        r = requests.get("{}/size".format(self.__endpoint))
        if r.status_code == 200:
            data = r.json()
            return data['size']
        else:
            return 0
