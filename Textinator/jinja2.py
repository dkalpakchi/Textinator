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
from django.utils.functional import lazy
from django.template.loader import get_template


from jinja2 import Environment, Template, Markup


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

    template = get_template('partials/components/controls/markers/{}.html'.format(marker_variant.anno_type.replace('-', '_')))
    return Markup(template.render(context=ctx))

def display_relation(rel):
    template = Template("""
    <div class="relation tags has-addons" data-b="{{rel.between}}" data-d="{{rel.direction}}" data-r="{{rel.id}}"
        data-shortcut="{{rel.shortcut|upper}}">
      <span class="tag arrow is-grey">&#8594;</span>
      <span class="tag is-black">{{rel.name}}</span>
      {% if rel.shortcut %}
        <span class="tag is-dark">{{rel.shortcut|upper}}</span>
      {% endif %}
    </div>
    """)
    return Markup(template.render(rel=rel))


def prettify(value):
    """Converts newlines into <p> and <br />s."""
    md = markdown.markdown(value)
    # Bulmify things
    md = md.replace('<h1>', '<h1 class="title is-4">')
    md = md.replace('<h2>', '<h2 class="title is-5">')
    md = md.replace('<h3>', '<h3 class="title is-6">')
    return Markup(md)


def naturaltime(value):
    # TODO: this doesn't localize for some reason!
    return NaturalTimeFormatter.string_for(value)


def lang_local_name(code):
    # {'bidi': False, 'code': 'sv', 'name': 'Swedish', 'name_local': 'svenska', 'name_translated': 'Swedish'}
    return translation.get_language_info(str(code))['name_local']


def lang_translated_name(code):
    # {'bidi': False, 'code': 'sv', 'name': 'Swedish', 'name_local': 'svenska', 'name_translated': 'Swedish'}
    return translation.get_language_info(str(code))['name_translated']


def environment(**options):
    extensions = [] if 'extensions' not in options else options['extensions']
    extensions.append('sass_processor.jinja2.ext.SassSrc')
    extensions.append('jinja2.ext.i18n')
    extensions.append('jinja2.ext.with_')
    options['extensions'] = extensions
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'now': pytz.UTC.localize(datetime.now())
    })
    env.filters['url_path'] = get_path
    env.filters['display_marker'] = display_marker_variant
    env.filters['display_relation'] = display_relation
    env.filters['prettify'] = prettify
    env.filters['bool2str'] = lambda x: str(x).lower()
    env.filters['any'] = any
    env.filters['all'] = all
    env.filters['naturaltime'] = naturaltime
    env.filters["local_language_name"] = lang_local_name
    env.filters['translated_language_name'] = lang_translated_name

    env.install_gettext_translations(translation)

    # i18n template functions
    env.install_gettext_callables(gettext=gettext, ngettext=ngettext,
        newstyle=True)
    return env