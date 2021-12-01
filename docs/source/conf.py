# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import os
import sys
import inspect
from pathlib import Path

import django
from django.utils.html import strip_tags
from django.utils.encoding import force_text

sys.path.insert(0, str(Path(__file__).parents[2]))
print("PATH", sys.path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'Textinator.settings'
django.setup()

# Auto list fields from django models - from https://djangosnippets.org/snippets/2533/#c5977
def process_docstring(app, what, name, obj, options, lines):
    # This causes import errors if left outside the function
    from django.db import models

    # Only look at objects that inherit from Django's base model class
    if inspect.isclass(obj) and issubclass(obj, models.Model):
        # Grab the field list from the meta class
        fields = obj._meta.get_fields()

        for field in fields:
            # Skip ManyToOneRel and ManyToManyRel fields which have no 'verbose_name' or 'help_text'
            if not hasattr(field, 'verbose_name'):
                continue

            # Decode and strip any html out of the field's help text
            help_text = strip_tags(force_text(field.help_text))

            # Decode and capitalize the verbose name, for use if there isn't
            # any help text
            verbose_name = force_text(field.verbose_name).capitalize()

            if help_text:
                # Add the model field to the end of the docstring as a param
                # using the help text as the description
                lines.append(u':param %s: %s' % (field.attname, help_text))
            else:
                # Add the model field to the end of the docstring as a param
                # using the verbose name as the description
                lines.append(u':param %s: %s' % (field.attname, verbose_name))

            # Add the field's type to the docstring
            if isinstance(field, models.ForeignKey):
                to = field.related_model
                lines.append(u':type %s: %s to :class:`~%s.%s`' % (field.attname, type(field).__name__, to.__module__, to.__name__))
            else:
                lines.append(u':type %s: %s' % (field.attname, type(field).__name__))

    # Return the extended docstring
    return lines

def setup(app):
    # Register the docstring processor with sphinx
    app.connect('autodoc-process-docstring', process_docstring)

# END Auto list fields from django models -


# -- Project information -----------------------------------------------------

project = 'Textinator'
copyright = '2021, Dmytro Kalpakchi'
author = 'Dmytro Kalpakchi'

# The full version, including alpha/beta/rc tags
release = '0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
	'sphinx.ext.autodoc',
	'sphinx.ext.autosummary'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'karma_sphinx_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']