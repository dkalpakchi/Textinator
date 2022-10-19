# -*- coding: utf-8 -*-
#
# This is a file for helpers that could potentially be used as post-processing methods for data sources
#

import re
import string
import json
import hashlib
import requests


# TODO: fix collisions sometimes
def hash_text(text):
    m = hashlib.sha256()
    if isinstance(text, str):
        m.update(text.encode('utf8'))
    else:
        m.update(str(text).encode('utf8'))
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
    return wiki_text


def remove_empty_lines(text):
    text = text.replace(u'\u00a0', '')
    return re.sub('\n{3,}', '\n\n', text)


def apply_premarkers(proj, text):
    punct = string.punctuation
    for c in list("\\$[]()*+/?-.\"\'|^"):
        punct = punct.replace(c, "\{}".format(c))

    premarker_tmpl = "<span class='tag is-medium' data-s='{}' data-i='NA' style='background-color:{}; color: {}'>{}<button class='delete is-small'></button></span>"
    for pm in proj.premarker_set.all():
        m, tokens = pm.marker, pm.tokens.split(',')
        h = m.color.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        # https://www.w3.org/TR/AERT/#color-contrast
        # https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color
        brightness = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]
        text_color = 'black' if brightness > 125 else 'white'
        for tok in tokens:
            for t in (tok.lower(), tok.capitalize()):
                text = re.sub("(?<=[{0} ]){1}(?=[{0} ])".format(punct, t),
                    premarker_tmpl.format(m.code, m.color, text_color, t),
                    text)
    return text


def make_checker(self, param, value):
    def _function():
        return getattr(self, param) == value
    return _function


def custom_or_default(fallback, prop):
    def _inner(func):
        def _inner2(self):
            default = func(self)
            if hasattr(self, fallback):
                return default or getattr(getattr(self, fallback), prop)
            else:
                return default
        return _inner2
    return _inner
