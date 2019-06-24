import json


class AbsentSpecError(Exception):
    pass


class DataSource:
    def __init__(self, spec_data):
        self.__spec = json.loads(spec_data)
        self.__data = []

        self._required_keys = []

    def check_constraints(self):
        absent = []
        for k in self._required_keys:
            if k not in self.__spec:
                absent.append(k)

        if absent:
            raise AbsentSpecError("Required keys are missing: {}".format(", ".join(self._required_keys)))

    def get_spec(self, key):
        return self.__spec.get(key)

    def _add_datapoint(self, txt):
        self.__data.append(txt)

    def data(self):
        return self.__data

    def __getitem__(self, key):
        return self.__data[key]


class TextFileSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['files']
        self.check_constraints()

        for fname in self.get_spec('files'):
            with open(fname) as f:
                self._add_datapoint(f.read())


class ElasticSource(DataSource):
    pass


class DbSource(DataSource):
    pass


class JsonSource(DataSource):
    pass

