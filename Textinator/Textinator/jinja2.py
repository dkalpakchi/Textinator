# -*- coding: utf-8 -*-
import re
import pytz
import markdown
from datetime import datetime
from urllib.parse import urlparse

from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.humanize.templatetags.humanize import NaturalTimeFormatter
from django.utils.translation import gettext, ngettext
from django.urls import reverse
from django.utils import translation
from django.template.loader import get_template


from jinja2 import Environment, Template
from markupsafe import Markup


INSIDE_PROJECT_RE = re.compile(r"/projects/\d+/?$")


def get_path(url):
    return urlparse(url).path

def display_marker_variant(marker_variant, **kwargs):
    h = marker_variant.color.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    # https://www.w3.org/TR/AERT/#color-contrast
    # https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color
    brightness = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]
    text_color = 'black' if brightness > 125 else 'white'

    ctx = {
        'marker': marker_variant,
        'text_color': text_color
    }
    ctx.update(kwargs)

    template = get_template('partials/components/controls/markers/{}.html'.format(
        marker_variant.anno_type.replace('-', '_')
    ))
    return Markup(template.render(context=ctx))

def display_relation(rel):
    template = Template("""
    <div class="relation tags has-addons" data-b="{{rel.between}}" data-d="{{rel.direction}}" data-r="{{rel.id}}"
        data-shortcut="{{rel.shortcut|upper}}">
      <span class="tag arrow is-grey">&#8594;</span>
      <span data-role="name" class="tag is-black">{{rel.name}}</span>
      {% if rel.shortcut %}
        <span class="tag is-dark">{{rel.shortcut|upper}}</span>
      {% endif %}
    </div>
    """)
    return Markup(template.render(rel=rel))

# TODO: re-think custom tags
CUSTOM_MD_TAGS = {
    'pin': {
        'core': "!---!",
        'template': "<div class='scrollable'>{scrollable}</div><div class='pinned'>{pinned}</div>"
    },
    'pin_up': {
        'core': "!-^-!",
        'template': "<div class='pinned'>{pinned}</div><div class='scrollable'>{scrollable}</div>"
    }
}

for tag in CUSTOM_MD_TAGS:
    CUSTOM_MD_TAGS[tag]['tag'] = "\n{}\n".format(CUSTOM_MD_TAGS[tag]['core'])
    CUSTOM_MD_TAGS[tag]['replace'] = "%/{}/%".format(CUSTOM_MD_TAGS[tag]['core'])

def to_markdown(value):
    """Converts newlines into <p> and <br />s."""
    # replace all newlines from custom tags to keep them
    for tag in CUSTOM_MD_TAGS.values():
        if tag['tag'] in value:
            value = value.replace(tag['tag'], tag['replace'])

    value = value.replace("\n", "<br>")
    md = markdown.markdown(value)
    # Bulmify things
    md = md.replace('<h1>', '<h1 class="title is-4">')
    md = md.replace('<h2>', '<h2 class="title is-5">')
    md = md.replace('<h3>', '<h3 class="title is-6">')

    # This is because it is hard to maintain marking over <p>
    # so instead we will replace them with <br>
    for spec in CUSTOM_MD_TAGS.values():
        md = md.replace("<p>", "")\
                .replace("(?!{})</p>".format(spec['core']), "<br>")\
                .replace("</p>", "")
        md = re.sub(
            r'{}</li>'.format(spec['core']),
            '</li>{}'.format(spec['replace']), md)

        if spec['replace'] in md:
            scrollable, pinned = md.split(spec['replace'])
            scrollable, pinned = scrollable.strip(), pinned.strip()

            scrollable = re.sub("\n(?!<)", "<br>", scrollable)
            pinned = re.sub("(</?(li|ol|ul)>)", "", pinned)
            pinned = re.sub("\n(?!<)", "<br>", pinned)

            md = spec['template'].format(
                scrollable=scrollable, pinned=pinned
            )

    return Markup(md)

def to_formatted_text(value):
    if PIN_MD_TAG in value:
        scrollable, pinned = value.split(PIN_MD_TAG)
        return "<div class='scrollable pre-formatted-text'>{}</div><div class='pinned pre-formatted-text'>{}</div>".format(
            scrollable.strip(), pinned.strip()
        )
    else:
        return "<p class='pre-formatted-text'>{}</p>".format(value)

def wrap_paragraph(value):
    return "<p>{}</p>".format(value)

def naturaltime(value):
    # TODO: this doesn't localize for some reason!
    return NaturalTimeFormatter.string_for(value)

def lang_local_name(code):
    # {'bidi': False, 'code': 'sv', 'name': 'Swedish', 'name_local': 'svenska', 'name_translated': 'Swedish'}
    return translation.get_language_info(str(code))['name_local']

def lang_translated_name(code):
    # {'bidi': False, 'code': 'sv', 'name': 'Swedish', 'name_local': 'svenska', 'name_translated': 'Swedish'}
    return translation.get_language_info(str(code))['name_translated']

def markify(score):
    if isinstance(score, int):
        mapping = [
            ('none', 'times', 'danger', '', ''),
            ('limited', 'check', 'orange', '[', ']'),
            ('moderate', 'check', 'darkyellow', '(', ')'),
            ('extensive', 'check', 'success', '', '')
        ]
        return '<span title="{0}" class="icon has-text-{2}">{3}<i class="fas fa-{1}"></i>{4}</span>'.format(*mapping[score])
    else:
        if score == 'docker':
            return '<i class="fab fa-{}"></i>'.format(score)
        else:
            return '<i class="fas fa-{}"></i>'.format(score)

def is_list(val):
    return isinstance(val, list)

def is_inside(path):
    return bool(re.search(INSIDE_PROJECT_RE, path))

def from_ts(ts):
    return datetime.fromtimestamp(float(ts))

def to_list(x):
    return list(x)

def to_camelcase(x):
    return "".join([w if i == 0 else w.title() for i, w in enumerate(x.split())])

def strip(x):
    return str(x).strip()

def environment(**options):
    extensions = [] if 'extensions' not in options else options['extensions']
    extensions.append('jinja2.ext.i18n')
    options['extensions'] = extensions
    options['autoescape'] = True
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'now': pytz.UTC.localize(datetime.now(), is_dst=False)
    })
    env.filters['url_path'] = get_path
    env.filters['display_marker'] = display_marker_variant
    env.filters['display_relation'] = display_relation
    env.filters['to_markdown'] = to_markdown
    env.filters['to_formatted_text'] = to_formatted_text
    env.filters['wrap_paragraph'] = wrap_paragraph
    env.filters['bool2str'] = lambda x: str(x).lower()
    env.filters['any'] = any
    env.filters['all'] = all
    env.filters['naturaltime'] = naturaltime
    env.filters["local_language_name"] = lang_local_name
    env.filters['translated_language_name'] = lang_translated_name
    env.filters["markify"] = markify
    env.filters["is_list"] = is_list
    env.filters["is_inside"] = is_inside
    env.filters["from_ts"] = from_ts
    env.filters["to_list"] = to_list
    env.filters["camelcase"] = to_camelcase
    env.filters['strip'] = strip

    env.install_gettext_translations(translation)

    # i18n template functions
    env.install_gettext_callables(gettext=gettext, ngettext=ngettext,
        newstyle=True)

    env.trim_blocks = True
    env.lstrip_blocks = True
    return env
