import re
import pytz
import markdown
from datetime import datetime
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.translation import gettext, ngettext
from django.urls import reverse
from urllib.parse import urlparse

from jinja2 import Environment, Template, Markup


def get_path(url):
    return urlparse(url).path


def display_marker(marker):
    h = marker.color.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    # https://www.w3.org/TR/AERT/#color-contrast
    # https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color
    brightness = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]
    text_color = 'black' if brightness > 125 else 'white'

    template = Template("""
    <div class="marker tags has-addons" data-s="{{marker.short}}" data-color="{{marker.color}}" data-text-color="{{text_color}}" data-res="{{marker.get_count_restrictions()}}"
        data-shortcut="{{marker.shortcut|upper}}" data-submittable="{% if not marker.is_part_of_relation() %}true{% else %}false{% endif %}">
      {% if marker.is_part_of_relation() %}
        <span class="tag arrow is-grey"><input type="checkbox"></span>
      {% endif %}
      <span class="tag" style="background-color: {{marker.color}}; color: {{text_color}};">{{marker.name}}</span>
      {% if marker.shortcut %}
        <span class="tag is-dark">{{marker.shortcut|upper}}</span>
      {% endif %}
    </div>
    """)
    return Markup(template.render(marker=marker, text_color=text_color))


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


def environment(**options):
    extensions = [] if 'extensions' not in options else options['extensions']
    extensions.append('sass_processor.jinja2.ext.SassSrc')
    extensions.append('jinja2.ext.i18n')
    options['extensions'] = extensions
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'now': pytz.UTC.localize(datetime.now())
    })
    env.filters['url_path'] = get_path
    env.filters['display_marker'] = display_marker
    env.filters['display_relation'] = display_relation
    env.filters['prettify'] = prettify
    env.filters['bool2str'] = lambda x: str(x).lower()
    env.filters['any'] = any
    env.filters['all'] = all
    # i18n template functions
    env.install_gettext_callables(gettext=gettext, ngettext=ngettext,
        newstyle=True)
    return env