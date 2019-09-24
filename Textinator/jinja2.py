import re
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from urllib.parse import urlparse

from jinja2 import Environment, Template, Markup


def get_path(url):
    return urlparse(url).path


def display_marker(marker):
    template = Template("""
    <div class="marker tags has-addons" data-s="{{marker.short}}" data-color="{{marker.color}}"
        data-shortcut="{{marker.shortcut|upper}}" data-submittable="{{not marker.is_part_of_relation()}}">
      <span class="tag is-{{marker.color}}">{{marker.name}}</span>
      {% if marker.shortcut %}
        <span class="tag is-dark">{{marker.shortcut|upper}}</span>
      {% endif %}
    </div>
    """)
    return Markup(template.render(marker=marker))


def display_relation(rel):
    template = Template("""
    <div class="relation tags has-addons" data-b="{{rel.between}}" data-d="{{rel.direction}}" data-r="{{rel.id}}">
        <span class="tag arrow is-grey">&#8594;</span>
        <span class="tag is-dark">{{rel.name}}</span>
    </div>
    """)
    return Markup(template.render(rel=rel))


def linebreaks(value):
    """Converts newlines into <p> and <br />s."""
    value = re.sub(r'\r\n|\r|\n', '\n', value) # normalize newlines
    paras = re.split('\n{2,}', value)
    paras = [u'<p>{}</p>'.format(p.replace('\n', '<br />')) for p in paras]
    paras = u'\n\n'.join(paras)
    return Markup(paras)


def environment(**options):
    extensions = [] if 'extensions' not in options else options['extensions']
    extensions.append('sass_processor.jinja2.ext.SassSrc')
    options['extensions'] = extensions
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
    })
    env.filters['url_path'] = get_path
    env.filters['display_marker'] = display_marker
    env.filters['display_relation'] = display_relation
    env.filters['linebreaks'] = linebreaks
    return env