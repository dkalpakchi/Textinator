#
# This is a file for helpers that could potentially be used as post-processing methods for data sources
#

import re
import json
import hashlib
import requests
from django.template.defaultfilters import linebreaksbr


def hash_text(text):
    m = hashlib.sha256()
    if isinstance(text, str):
        m.update(text.encode('utf8'))
    else:
        m.update(str(text))
    return m.hexdigest()


def retrieve_by_hash(key, model_cls, cache):
    key_hash = hash_text(key)
    obj_id = cache.get(key_hash)
    try:
        if obj_id:
            obj = model_cls.objects.get(pk=obj_id)
        else:
            obj = model_cls.objects.get(content=key)
            cache.set(obj.content_hash, obj.pk, 600)
    except model_cls.DoesNotExist:
        obj = None
    return obj


def truncate(value, limit=80):
    """
    Truncates a string after a given number of chars keeping whole words.
    """
    
    try:
        limit = int(limit)
    # invalid literal for int()
    except ValueError:
        # Fail silently.
        return value
    
    # Return the string itself if length is smaller or equal to the limit
    if len(value) <= limit:
        return value
    
    # Cut the string
    value = value[:limit]
    
    # Break into words and remove the last
    words = value.split(' ')[:-1]
    
    # Join the words and return
    return ' '.join(words) + '...'


def filter_wiki_markup(markup):
    # parse Wikimedia markup
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post('http://localhost:3000', data=json.dumps({'wikitext': markup}), headers=headers)
    wiki_text = re.sub('(""|\'\'|\*(?=\n+))', '', re.sub('\n{3,}', '\n', r.text))
    return linebreaksbr(wiki_text)