import os
import requests
import glob
import json
import random
import pymysql
import pymongo


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
            if k not in self.__spec:
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
        pass

    def size(self):
        return self.__size

    def __getitem__(self, key):
        return self.__data[key]


class PlainTextSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)
        self._required_keys = ['texts']
        self.check_constraints()

        for text in self.get_spec('texts'):
            self._add_datapoint(text)

    def get_random_datapoint(self):
        return self[random.randint(0, self.size() - 1)]


class TextFileSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)

        self._required_keys = ['files']
        self.check_constraints()

        for fname in self.get_spec('files'):
            with open(fname) as f:
                self._add_datapoint(f.read())

    def get_random_datapoint(self):
        return self[random.randint(0, self.size() - 1)]

    def size(self):
        return len(self.__data)


class DbSource(DataSource):
    def __init__(self, spec_data):
        super().__init__(spec_data)
        self._required_keys = ['db_type', 'user', 'password', 'database']
        self._aux_keys = [('collection', 'field'), ('rand_dp_query', 'size_query')]
        self.check_constraints()

        self.__db_type = self.get_spec('db_type')
        self.__user = self.get_spec('user')
        self.__database = self.get_spec('database')
        self.__collection = self.get_spec('collection')
        self.__field = self.get_spec('field')
        self.__rand_dp_query = self.get_spec('rand_dp_query')
        self.__size_query = self.get_spec('size_query')
        # TODO: make safer
        self.__password = self.get_spec('password')
        self.__conn = self.__connect()
        self.__ids = None
        self.__N = None

    def __connect(self):
        try:
            return {
                'mysql': self.__connect_mysql,
                'mongodb': self.__connect_mongo
            }[self.__db_type]()
        except AttributeError:
            raise NotImplementedError('{} is not supported'.format(self.__db_type)) from None

    def __connect_mysql(self):
        return pymysql.connect(user=self.__user, database=self.__database, password=self.__password)

    def __connect_mongo(self):
        # TODO: add authentication
        return pymongo.MongoClient("mongodb://localhost:27017/")

    #
    # SELECT old_text AS ARTICLE
    # FROM (
    #   SELECT page_title, page_latest, page_id
    #   FROM page WHERE page_is_redirect = 0 AND page_len > 3000
    # ) pg INNER JOIN text ON page_latest = old_id WHERE page_id >= ROUND(RAND() * (SELECT MAX(page_id) FROM page)) LIMIT 1;
    #
    def get_random_datapoint(self):
        # self.cache_datapoint_ids()
        if self.__rand_dp_query:
            cur = self.__conn.cursor()
            cur.execute(self.__rand_dp_query)
            text = cur.fetchone()[0]
            cur.close()
            return text.decode('utf8')
        elif self.__db_type == 'mongodb':
            db = self.__conn[self.__database]
            collection = db[self.__collection]
            cursor = collection.aggregate([{ "$sample": { "size": 1 } }])
            return list(cursor)[0][self.__field]
        else:
            raise NotImplementedError('Please set `rand_dp_query` in your settings')

    def size(self):
        if self.__size_query:
            cur = self.__conn.cursor()
            cur.execute(self.__size_query)
            count = cur.fetchone()[0]
            cur.close()
            return count
        elif self.__db_type == 'mongodb':
            db = self.__conn[self.__database]
            collection = db[self.__collection]
            return collection.count()

    def get_datapoints(self, query):
        texts = []
        with self.__conn.cursor() as cur:
            cur.execute(query)
            for text in cur:
                texts.append(text)
        return texts


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
                print(content_type)

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
        return self[random.randint(0, self.size() - 1)]

