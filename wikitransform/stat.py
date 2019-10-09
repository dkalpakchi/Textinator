import re
import string
import operator
import random
from collections import defaultdict

import pymongo
import matplotlib.pyplot as plt
import seaborn as sns


def plot_histogram(arr, title=None, xlim_min=None, xlim_max=None, bins_step=None):
    plt.figure()

    N = len(arr)

    # kwargs = {
    #     'kde': False
    # }
    # if xlim_min and xlim_max:
    #     plt.xlim(xlim_min, xlim_max)
    #     if bins_step:
    #         kwargs['bins'] = list(range(xlim_min, xlim_max, bins_step))

    plt.xlim(xlim_min, xlim_max)

    ax = sns.distplot(arr, kde=False, bins=list(range(xlim_min, xlim_max, bins_step)))
    s = 0
    for p in ax.patches:
        s+= p.get_height()

    for p in ax.patches: 
        ax.text(p.get_x() + p.get_width()/2.,
                p.get_height(),
                '{}'.format(int(p.get_height()*N/s)), 
                fontsize=4,
                color='red',
                ha='center',
                va='bottom')

    plt.savefig(title or 'diagram.pdf')


DB_NAME = 'svwiki'
DB_COLLECTION = 'articles'
mongoc = pymongo.MongoClient("mongodb://localhost:27017/")

dblist = mongoc.list_database_names()
if DB_NAME in dblist:
    print("The database {} exists.".format(DB_NAME))

mongo_svwiki = mongoc[DB_NAME]

colist = mongo_svwiki.list_collection_names()
if DB_COLLECTION in colist:
    print("The collection {} exists in the database {}.".format(DB_COLLECTION, DB_NAME))
mongo_articles = mongo_svwiki[DB_COLLECTION]


cursor = mongo_articles.aggregate([{ "$project" : { "page_id": 1, "page_title": 1, "text": 1}}])#, "text_len" : { "$strLenCP": "$text" }}}])

text_word_lengths = []
for page in cursor:
    word_length = len(list(filter(lambda x: x, re.split(r'[{}]'.format(string.punctuation), page['text']))))
    # text_char_lengths.append(page["text_len"])
    text_word_lengths.append(word_length)

# twl = sorted(text_word_lengths.items(), key=operator.itemgetter(1))
# l = list(set([x[1] for x in twl]))
# l.sort()

# v = defaultdict(list)
# for key, value in twl:
#     v[value].append(key)

# twl = dict(twl)

# idx = range(0, len(l))

# samples = []
# for _ in range(1000000):
#     i = random.sample(idx, 1)[0]
#     k = random.sample(v[l[i]], 1)[0]
#     samples.append(twl[k])

plot_histogram(text_word_lengths, xlim_min=0, xlim_max=300, bins_step=10)

