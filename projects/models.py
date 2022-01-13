import random
import time
import re
import string
import json
import hashlib
from datetime import datetime
from collections import defaultdict

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import caches
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tinymce import HTMLField
from filebrowser.fields import FileBrowseField
from colorfield.fields import ColorField

from .datasources import *
from .helpers import *


class CommonModel(models.Model):
    dt_created = models.DateTimeField(null=True, default=timezone.now, verbose_name=_("Created at"),
        help_text=_("Autofilled"))
    dt_updated = models.DateTimeField(null=True, verbose_name=_("Updated at"),
        help_text=_("Autofilled"))

    class Meta:
        abstract = True

    def to_json(self, dt_format=None):
        return {
            'created': self.dt_created.strftime(dt_format),
            'updated': self.dt_updated.strftime(dt_format)
        } if dt_format else {}

    def save(self, *args, **kwargs):
        self.dt_updated = timezone.now()
        super(CommonModel, self).save(*args, **kwargs)


class PostProcessingMethod(CommonModel):
    class Meta:
        verbose_name = _('post-processing method')
        verbose_name_plural = _('post-processing methods')

    name = models.CharField(_("name"), max_length=50,
        help_text=_("Verbose name"))
    helper = models.CharField(_("helper function name"), max_length=50,
        help_text=_("Name as specified in `projects/helpers.py`"))

    def __str__(self):
        return self.name


# Create your models here.
class DataSource(CommonModel):
    class Meta:
        verbose_name = _('data source')
        verbose_name_plural = _('data sources')
        permissions = (
            ('view_this_datasource', 'View this data source'),
            ('change_this_datasource', 'Change this data source'),
            ('delete_this_datasource', 'Delete this data source'),
        )

    name = models.CharField(_("dataset name"), max_length=50)
    source_type = models.CharField(_("dataset type"), max_length=10, choices=settings.DATASOURCE_TYPES)
    spec = models.TextField(_("specification"), null=False,
        help_text=_("in a JSON format")) # json spec of the data source
    post_processing_methods = models.ManyToManyField(PostProcessingMethod, blank=True,
        verbose_name=_("post-processing methods"))
    language = models.CharField(_("language"), max_length=10, choices=settings.LANGUAGES,
        help_text=_("Language of this data source")
    )
    formatting = models.CharField(_('formatting'), max_length=3, choices=settings.FORMATTING_TYPES,
        help_text=_("text formating of the data source"))
    is_public = models.BooleanField(_("is public?"), default=False,
        help_text=_("Whether to make data source available to other Textinator users"))

    @classmethod
    def type2class(cls, source_type):
        return globals().get(source_type + 'Source')

    def postprocess(self, text):
        pp = self.post_processing_methods.all()
        if pp:
            for method in pp:
                text = globals().get(method.helper, lambda x: x)(text)
        return text

    def get(self, idx):
        source_cls = DataSource.type2class(self.source_type)
        if source_cls:
            ds_instance = source_cls(self.spec.replace('\r\n', ' ').replace('\n', ' '))
        return ds_instance[idx]

    def size(self):
        source_cls = DataSource.type2class(self.source_type)
        ds_instance = source_cls(self.spec.replace('\r\n', ' ').replace('\n', ' '))
        return ds_instance.size()

    def __str__(self):
        return "{} ({})".format(self.name, self.language)


class MarkerAction(CommonModel):
    class Meta:
        verbose_name = _('marker action')
        verbose_name_plural = _('marker actions')

    name = models.CharField(_("name"), max_length=50, unique=True)
    description = models.TextField(_("description"), null=False)
    file = models.CharField(_("file name"), max_length=100,
        help_text=_("a name of the JS plugin file in the `/static/scripts/labeler_plugins` directory"))
    admin_filter = models.CharField(_("type of admin filter"), max_length=50, blank=True, null=True,
        help_text=_(
            """
            Specifies the filter type in the data explorer interface (one of 'boolean', 'range').
            If empty, then this action will be excluded from data explorer.
            """
        )) # What types? So far found: boolean, range

    def __str__(self):
        return self.name

    def to_json(self, dt_format=None):
        res = super(MarkerAction, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name,
            'admin_filter': self.admin_filter
        })
        return res


class Marker(CommonModel):
    """
    This model holds the **definition** for each unit of annotation in Textinator, called `Marker`.
    We create each `Marker` only when creating a new project and can re-use `Markers` between the projects.
    """
    name = models.CharField(_("name"), max_length=50,
        help_text=_("The display name of the marker (max 50 characters)"))
    code = models.CharField(_("code"), max_length=25, unique=True, blank=True,
        help_text=_("Marker's nickname used internally"))
    color = ColorField(_("color"), help_text=_("Color for the annotated text span"))
    shortcut = models.CharField(_("keyboard shortcut"), max_length=10, null=True, blank=True,
        help_text=_("Keyboard shortcut for annotating a piece of text with this marker"))
    suggestion_endpoint = models.URLField(max_length=200, null=True, blank=True,
        help_text=_("Endpoint for the Suggestions API"))

    class Meta:
        verbose_name = _('marker')
        verbose_name_plural = _('markers')
        permissions = (
            ('change_this_marker', 'Change this marker'),
            ('delete_this_marker', 'Delete this marker'),
        )


    def save(self, *args, **kwargs):
        if not self.code:
            self.code = "{}_{}_{}".format(self.name_en[:3].upper(), str(int(time.time())), random.randint(0, 9999))
        super(Marker, self).save(*args, **kwargs)

    def is_part_of_relation(self):
        """
        Check whether a given marker is part of definition for any `Relation`
        """
        return bool(Relation.objects.filter(models.Q(pairs__first=self) | models.Q(pairs__second=self)).all())

    def __str__(self):
        return self.__dict__['name']

    def to_minimal_json(self, dt_format=None):
        res = super(Marker, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name_en
        })
        return res

    def to_json(self, dt_format=None):
        res = super(Marker, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name_en,
            'color': self.color,
            'code': self.code
        })
        return res


class MarkerPair(CommonModel):
    class Meta:
        verbose_name = _('marker pair')
        verbose_name_plural = _('marker pairs')

    first = models.ForeignKey(Marker, related_name='first', on_delete=models.CASCADE)
    second = models.ForeignKey(Marker, related_name='second', on_delete=models.CASCADE)

    def __str__(self):
        return self.first.code + '-:-' + self.second.code


class Relation(CommonModel):
    class Meta:
        verbose_name = _('relation')
        verbose_name_plural = _('relations')
        permissions = (
            ('change_this_relation', 'Change this relation'),
            ('delete_this_relation', 'Delete this relation'),
        )

    name = models.CharField(_("name"), max_length=50)
    pairs = models.ManyToManyField(MarkerPair, verbose_name=_("marker pairs"))
    direction = models.CharField(_("direction"), max_length=1, choices=[
        ('0', _('Directed from the first to the second')),
        ('1', _('Directed from the second to the first')),
        ('2', _('Bi-directional'))
    ])
    shortcut = models.CharField(_("keyboard shortcut"), max_length=15, 
        help_text=_("Keyboard shortcut for marking a piece of text with this relation"), null=True, blank=True)
    representation = models.CharField(_("graphical representation type"), max_length=1,
        choices=[('g', _('Graph')), ('l', _('List'))], default='g',
        help_text=_("How should the relation be visualized?"))

    @property
    def between(self):
        return "|".join([str(p) for p in self.pairs.all()])

    def __str__(self):
        return self.__dict__['name']

    def to_json(self, dt_format=None):
        res = super(Relation, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name,
            'pairs': [str(p) for p in self.pairs.all()],
            'direction': self.direction
        })
        return res


class TaskTypeSpecification(CommonModel):
    class Meta:
        verbose_name = _('task type specification')
        verbose_name_plural = _('task type specification')
    task_type = models.CharField(_("type of the annotation task"), max_length=10, choices=settings.TASK_TYPES)
    config = models.JSONField(_("JSON configuration"))

    def __str__(self):
        dct = dict(settings.TASK_TYPES)
        return "Specification for {}".format(dct[self.task_type])


class Project(CommonModel):
    class Meta:
        verbose_name = _('project')
        verbose_name_plural = _('projects')
        ordering = ['-dt_finish']
        permissions = (
            ('view_this_project', 'Can view this project'),
        )


    title = models.CharField(_("title"), max_length=50)
    short_description = models.TextField(_("short description"), max_length=1000, default="",
        help_text=_("Will be displayed on the project card"))
    institution = models.CharField(_("institution"), max_length=500, null=True, blank=True,
        help_text=_("Institution responsible for the project"))
    supported_by = models.CharField(_("supported by"), max_length=1000, null=True, blank=True,
        help_text=_("The name of the organization supporting the project financially (if applicable)"))
    guidelines = HTMLField(_("guidelines"), null=True, blank=True,
        help_text=_("Guidelines for the annotation task"))
    reminders = HTMLField(_("reminders"), null=True, blank=True,
        help_text=_("Reminders for essential parts of guidelines (keep them short and on point)"))
    temporary_message = HTMLField(_("temporary message"), null=True, blank=True,
        help_text=_("A temporary message for urgent communication with annotators (e.g., about maintenance work)"))
    sampling_with_replacement = models.BooleanField(_("should data be sampled with replacement?"), default=False)
    disjoint_annotation = models.BooleanField(_("should disjoint annotation be allowed?"), default=False)
    show_dataset_identifiers = models.BooleanField(_("should dataset identifiers be shown?"), default=False)
    task_type = models.CharField(_("type of the annotation task"), max_length=10, choices=settings.TASK_TYPES)
    dt_publish = models.DateTimeField(verbose_name=_("to be published at")) # TODO: implement this functionality
    dt_finish = models.DateTimeField(verbose_name=_("to be finished at"))   # TODO: implement this functionality
    dt_updated = models.DateTimeField(_("updated at"), auto_now=True)
    collaborators = models.ManyToManyField(User, related_name='shared_projects', blank=True,
        verbose_name=_("collaborators"))
    participants = models.ManyToManyField(User, related_name='participations', through='UserProfile', blank=True,
        verbose_name=_("participants"))
    markers = models.ManyToManyField(Marker, through='MarkerVariant', blank=True,
        verbose_name=_("project-specific markers"))
    relations = models.ManyToManyField(Relation, through='RelationVariant', blank=True,
        verbose_name=_("project-specific relations"))
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("author"))
    datasources = models.ManyToManyField(DataSource, verbose_name=_("data sources"),
        help_text=_("All data sources must be of the same language as the project"))
    is_open = models.BooleanField(_("should the project be public?"), default=False)
    is_peer_reviewed = models.BooleanField(_("should the annotations be peer reviewed?"), default=False)
    allow_selecting_labels = models.BooleanField(_("should selecting the labels be allowed?"), default=False)
    disable_submitted_labels = models.BooleanField(_("should submitted labels be disabled?"), default=True)
    max_markers_per_input = models.PositiveIntegerField(_("maximal number of markers per input"), null=True, blank=True) # TODO: obsolete?
    round_length = models.PositiveIntegerField(_("round length"), null=True, blank=True,
        help_text=_("The number of text snippets consituting one round of the game"))
    points_scope = models.CharField(_("points scope"), max_length=2,
        choices=[('n', 'No points'), ('i', 'Per input'), ('l', 'Per label')],
        help_text=_("The scope of the submitted task"))
    points_unit = models.PositiveIntegerField(_("points' unit"), default=1,
        help_text=_("Number of points per submitted task"))
    has_intro_tour = models.BooleanField(_("should the project include intro tour?"), default=False,
        help_text=_("WARNING: Intro tours are currently in beta"))
    language = models.CharField(_("language"), max_length=10, choices=settings.LANGUAGES,
        help_text=_("Language of this project")
    )
    thumbnail = models.ImageField(null=True, blank=True, upload_to ='uploads/%Y/%m/%d/',
        help_text=_("A thumbnail of your project (ignored if not provided)"))
    video_summary = FileBrowseField(_("summary video"), max_length=1000, null=True, blank=True,
        help_text=_("Video introducing people to the annotation task at hand (if applicable)"))
    video_remote = models.URLField(max_length=200, null=True, blank=True,
        help_text=_("A URL for video summary to be embedded (e.g. from YouTube)"))


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def free_markers(self):
        return self.markervariant_set.filter(unit=None).order_by('anno_type')

    @property
    def marker_groups(self):
        return self.markervariant_set.exclude(unit=None).order_by('anno_type')

    def data(self, user):
        log = DataAccessLog.objects.filter(user=user, project=self, is_submitted=False, is_skipped=False).first()
        if log:
            ds = log.datasource
            dp_id = log.datapoint
            return ds.postprocess(ds.get(dp_id)).strip(), dp_id, ds.name, ds.size(), ds.pk

        dp_taboo = defaultdict(set)
        if not self.sampling_with_replacement:
            if self.disjoint_annotation:
                # TODO: check for race conditions here, could 2 annotators still get the same text?
                # meaning each user annotates whatever is not annotated
                logs = DataAccessLog.objects.filter(project=self).all()
            else:
                # meaning each user annotates all texts
                logs = DataAccessLog.objects.filter(project=self, user=user).all()
            for log in logs:
                dp_taboo[log.datasource.pk].add(log.datapoint)

        datasources = []
        for source in self.datasources.all():
            source_cls = DataSource.type2class(source.source_type)
            if source_cls:
                ds_instance = source_cls(source.spec.replace('\r\n', ' ').replace('\n', ' '))
                datasources.append((ds_instance, source.postprocess, source.pk))

        # take a random data point from data
        nds = len(datasources)

        # choose a dataset with a prior inversely proportional to the number of datapoints in them
        sizes = [datasources[i][0].size() for i in range(nds)]
        priors = [sizes[i] / sum(sizes) for i in range(nds)]
        priors_cumsum = [sum(priors[:i+1]) for i in range(len(priors))]

        rnd = random.random()
        ds_ind = sum([priors_cumsum[i] <= rnd for i in range(len(priors_cumsum))])

        ds, postprocess, idx = datasources[ds_ind]

        ds_ind_taboo, finished_all = set(), False
        if len(dp_taboo[idx]) >= sizes[ds_ind]:
            # try to select a new datasource that is not finished yet
            while len(dp_taboo[idx]) >= sizes[ds_ind]:
                # means this datasource is done, add it to the taboo list
                ds_ind_taboo.add(ds_ind)

                if len(ds_ind_taboo) >= nds:
                    # means we're done
                    finished_all = True
                    break

                while ds_ind in ds_ind_taboo:
                    rnd = random.random()
                    ds_ind = sum([priors_cumsum[i] <= rnd for i in range(len(priors_cumsum))])

                ds, postprocess, idx = datasources[ds_ind]

        if not finished_all:
            # get the id of the random datapoint and the datapoint itself
            dp_id, dp = ds.get_random_datapoint()

            if idx in dp_taboo:
                # get a random DP that is not in taboo list
                # NOTE: we stringify all datapoint ids for taboo for the sake of generality
                while str(dp_id) in dp_taboo[idx]:
                    dp_id, dp = ds.get_random_datapoint()

            # return:
            # -> a post-processed random datapoint from the chosen dataset
            # -> the point's id in the datasource
            # -> datasource size 
            # -> datasource id
            dp_source_name = ds.mapping[dp_id] if type(ds) == TextFileSource else False
            return postprocess(dp).strip(), dp_id, dp_source_name, ds.size(), idx
        else:
            return "NAN", -1, False, -1, -1
        
    def get_profile_for(self, user):
        try:
            return UserProfile.objects.get(project=self, user=user)
        except UserProfile.DoesNotExist:
            return None

    def has_participant(self, user):
        return user in self.participants.all()

    def shared_with(self, user):
        return user in self.collaborators.all()

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)
        try:
            spec_obj = TaskTypeSpecification.objects.get(task_type=self.task_type)
            spec = spec_obj.config
            for mspec in spec["markers"]:
                m = Marker.objects.get(code=mspec["id"])
                MarkerVariant.objects.get_or_create(marker=m, project=self, anno_type=mspec["anno_type"])
        except TaskTypeSpecification.DoesNotExist:
            pass

    def __str__(self):
        return self.title


class MarkerUnit(CommonModel):
    """
    Some annotation tasks might benefit from annotating groups of markers as one unit.
    This model stores the definitions of such units (shared across all users).

    The unit configuration has two dimensions:
    - marker group, which is defined by a one to many relationship with MarkerVariant model
    - unit height, which provides minimum and maximum number of marker groups in this unit

    `minimum_required` attribute defines a lower bound for a unit height, whereas `size` defines an upper bound.
    """

    class Meta:
        verbose_name = _('marker unit')
        verbose_name_plural = _('marker units')

    size = models.PositiveIntegerField(_("size"), default=1,
        help_text=_("Default (and maximal) number of marker groups in the unit"))
    minimum_required = models.PositiveIntegerField(_("minimum required"), default=1,
        help_text=_("Minimum required number of marker groups in the unit (can't be more than `size`)"))
    is_rankable = models.BooleanField(_("is rankable?"), default=False,
        help_text=_("Whether annotators should be allowed to rank marker groups in the unit"))

    @property
    def name(self):
        return "mn{}mx{}r{}".format(self.minimum_required, self.size, int(self.is_rankable))

    def __str__(self):
        suffix = " ({})".format(_("rankable")) if self.is_rankable else ""
        if self.size > self.minimum_required:
            return _("From {} to {}{}").format(self.minimum_required, self.size, suffix)
        elif self.size == self.minimum_required:
            return _("Exactly {}").format(self.minimum_required)

    def __lt__(self, other):
        return self.pk < other.pk


class Range(CommonModel):
    class Meta:
        verbose_name = _("range")
        verbose_name_plural = _("ranges")

    min_value = models.FloatField(verbose_name=_("minimal value"), blank=True, null=True)
    max_value = models.FloatField(verbose_name=_("maximal value"), blank=True, null=True)
    step = models.FloatField(verbose_name=_("step"), blank=True, null=True)

    def clean(self):
        if self.min_value is None and self.max_value is None and self.step is None:
            raise ValidationError(_("You must specify either a step, a minimal or a maximal value"))

    def __str__(self):
        res = ""
        if self.min_value is not None and self.max_value is not None:
            res = _("Between {} and {}").format(self.min_value, self.max_value)
        elif self.min_value is not None:
            res = _("From {}").format(self.min_value)
        elif self.max_value is not None:
            res = _("Up to {}").format(self.max_value)

        if self.step is not None:
            if res:
                res = "{} {}".format(res, "({})".format(_("step {}").format(self.step)))
            else:
                res = _("step {}").format(self.step).title()

        return res


class MarkerVariant(CommonModel):
    class Meta:
        unique_together = (('project', 'marker', 'unit'),)
        verbose_name = _("marker variant")

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE, verbose_name=_("marker template"))
    nrange = models.ForeignKey(Range, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("numeric range"),
        help_text=_(
            """
            Applicable only if the annotation types are 'integer', 'floating-point number' or 'range'.
            If the annotation type is 'range' and no numeric range is specified, the input will range from 0 to 100 by default.
            The values will remain unrestricted for 'integer' or 'floating-point number' types.
            """
        ))
    unit = models.ForeignKey(MarkerUnit, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_("marker unit"),
        limit_choices_to={})
    order_in_unit = models.PositiveIntegerField(_("order in a unit"), blank=True, null=True,
        help_text=_("Order of this marker in the unit"))
    actions = models.ManyToManyField(MarkerAction, through='MarkerContextMenuItem', blank=True,
        verbose_name=_("marker actions"),
        help_text=_("Actions associated with this marker"))
    are_suggestions_enabled = models.BooleanField(_("enable suggestions?"), default=False,
        help_text=_("Indicates whether Suggestions API should be enabled for this marker (if endpoint is specified)"))
    custom_suggestion_endpoint = models.URLField(
        max_length=200, null=True, blank=True,
        help_text=_(
            """
            Custom endpoint for the Suggestions API (by default the one from the marker template is used).
            Activates only if suggestions are enabled and the endpoint.
            """
        )
    )
    custom_color = ColorField(_("color"), null=True, blank=True,
        help_text=_("Customized color for the annotated text span (color of the marker template by default)"))
    custom_shortcut = models.CharField(_("keyboard shortcut"), max_length=10, null=True, blank=True,
        help_text=_("Keyboard shortcut for annotating a piece of text with this marker (shortcut of the marker template by default"))
    anno_type = models.CharField(_("annotation type"), max_length=10, default='m-span', choices=settings.ANNOTATION_TYPES,
        help_text=_("The type of annotations made using this marker"))

    def __init__(self, *args, **kwargs):
        super(MarkerVariant, self).__init__(*args, **kwargs)

        for atuple in settings.ANNOTATION_TYPES:
            at, _ = atuple
            setattr(self, 'is_{}'.format(at.replace('-','_')), make_checker(self, 'anno_type', at))

    @property
    def name(self):
        return self.marker.name

    @property
    @custom_or_default('marker', 'color')
    def color(self):
        return self.custom_color

    @property
    @custom_or_default('marker', 'shortcut')
    def shortcut(self):
        return self.custom_shortcut

    @property
    @custom_or_default('marker', 'suggestion_endpoint')
    def suggestion_endpoint(self):
        return self.custom_suggestion_endpoint

    @property
    def code(self):
        same_marker_pk = list(self.project.markervariant_set.filter(marker=self.marker).values_list('pk', flat=True))
        same_marker_pk.sort()
        return "{}_{}".format(self.marker.code, same_marker_pk.index(self.pk))


    def get_count_restrictions(self, stringify=True):
        """
        Get the restrictions (if any) on the number of markers per submitted instance
        
        Args:
            stringify (bool, optional): Whether to return the restrictions in a string format
        
        Returns:
            (str or list): Restrictions on the number of markers per submitted instance
        
        """
        try:
            restrictions = list(MarkerRestriction.objects.filter(variant=self).all())
        except MarkerVariant.DoesNotExist:
            return ''
        return '&'.join([str(r) for r in restrictions]) if stringify else restrictions

    def is_part_of_relation(self):
        return self.marker.is_part_of_relation()

    def save(self, *args, **kwargs):
        if hasattr(self, 'marker'):
            if self.color.lower() == self.marker.color.lower():
                self.custom_color = None

            if self.shortcut == self.marker.shortcut:
                self.custom_shortcut = None

            if self.suggestion_endpoint == self.marker.suggestion_endpoint:
                self.custom_suggestion_endpoint = None

        super(MarkerVariant, self).save(*args, **kwargs)

    def min(self):
        for r in self.markerrestriction_set.all():
            if r.kind == 'ge' or r.kind == 'eq':
                return r.value
            elif r.kind == 'gs':
                return r.value + 1
        return -1

    def max(self):
        for r in self.markerrestriction_set.all():
            if r.kind == 'le' or r.kind == 'eq':
                return r.value
            elif r.kind == 'ls':
                return r.value - 1
        return -1

    def __str__(self):
        return str(self.marker) + "<{}>".format(self.project.title)

    def to_minimal_json(self):
        res = self.marker.to_minimal_json()
        res['order'] = self.order_in_unit
        res['code'] = self.code
        return res

    def to_json(self):
        res = self.marker.to_json()
        res['order'] = self.order_in_unit
        res['code'] = self.code
        return res


class MarkerContextMenuItem(CommonModel):
    class Meta:
        verbose_name = _('marker context menu item')
        verbose_name_plural = _('marker context menu items')

    action = models.ForeignKey(MarkerAction, on_delete=models.CASCADE, verbose_name=_("marker action"))
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, verbose_name=_("marker"))
    verbose = models.CharField(_("verbose name"), max_length=50)
    verbose_admin = models.CharField(_("verbose name in data explorer"), max_length=50, null=True, blank=True)
    field = models.CharField(_("field name in logs"), max_length=50, null=True, blank=True,
        help_text=_("If applicable"))
    config = models.JSONField(_("JSON configuration"), null=True, blank=True)

    def to_json(self):
        data =  {
            'verboseName': self.verbose,
            'name': self.field or "{}_{}".format(self.action.name, self.pk),
            'file': self.action.file,
            'admin_filter': self.action.admin_filter
        }
        if self.config:
            data.update(self.config)
        return data


class MarkerRestriction(CommonModel):
    class Meta:
        verbose_name = _('marker restriction')
        verbose_name_plural = _("marker restrictions")

    variant = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, verbose_name=_("marker variant"))
    kind = models.CharField(_("restriction kind"), max_length=2, choices=[
        ('no', '-'), ('ls', '<'),
        ('le', '<='), ('gs', '>'),
        ('ge', '>='), ('eq', '=')
    ])
    value = models.PositiveIntegerField(_("restriction value"),
        help_text=_("e.g., if restriction kind is '<=' and value is '3', this creates a restriction '<= 3'"))

    def __str__(self):
        return self.kind + str(self.value)


class DataAccessLog(CommonModel):
    class Meta:
        verbose_name = _('data access log')
        verbose_name_plural = _("data access logs")

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("user"))
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    datapoint = models.CharField(_("datapoint ID"), max_length=64,
        help_text=_("As stored in the original dataset"))
    flags = models.TextField(_("flags"), default="",
        help_text=_("Internal behavior flags"))
    is_submitted = models.BooleanField(_("is submitted?"),
        help_text=_("Indicates whether the datapoint was successfully submitted by an annotator"))
    is_skipped = models.BooleanField(_("is skipped?"),
        help_text=_("Indicates whether the datapoint was skipped by an annotator"))


# TODO: put constraints on the markers - only markers belonging to project or task_type can be put!
# TODO: for one might want to mark pronouns 'det', 'den' iff they are really pronouns and not articles
#       maybe add a name of the boolean helper that lets you mark the word iff the helper returns true?
class PreMarker(CommonModel):
    class Meta:
        verbose_name = _('pre-marker')
        verbose_name_plural = _('pre-markers')

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE)
    tokens = models.TextField(_("static tokens"),
        help_text=_("Comma-separated tokens that should be highlighted with a marker"))


class RelationVariant(CommonModel):
    class Meta:
        unique_together = (('project', 'relation'),)
        verbose_name = _("relation variant")

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    relation = models.ForeignKey(Relation, on_delete=models.CASCADE, verbose_name=_("relation template"))
    custom_shortcut = models.CharField(_("keyboard shortcut"), max_length=15, null=True, blank=True,
        help_text=_("Keyboard shortcut for marking a piece of text with this relation (shortcut of the relation template by default)"))
    custom_representation = models.CharField(_("graphical representation type"), max_length=1,
        choices=[('g', _('Graph')), ('l', _('List'))], default='g',
        help_text=_("How should the relation be visualized? (representation of the relation template by default)"))

    @property
    @custom_or_default('relation', 'shortcut')
    def shortcut(self):
        return self.custom_shortcut

    @property
    @custom_or_default('relation', 'representation')
    def representation(self):
        return self.custom_representation

    def save(self, *args, **kwargs):
        if hasattr(self, 'relation'):
            if self.shortcut == self.relation.shortcut:
                self.custom_shortcut = None

            if self.custom_representation == self.relation.representation:
                self.custom_representation = None

        super(RelationVariant, self).save(*args, **kwargs)


class Context(CommonModel):
    class Meta:
        verbose_name = _('context')
        verbose_name_plural = _('contexts')

    datasource = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    datapoint = models.CharField(_("datapoint ID"), max_length=64, null=True, blank=True,
        help_text=_("As stored in the original dataset"))
    content = models.TextField(_("content"))

    @property
    def content_hash(self):
        return hash_text(self.content)

    def save(self, *args, **kwargs):
        super(Context, self).save(*args, **kwargs)

    def __str__(self):
        return truncate(self.content)

    def to_json(self):
        return {
            "ds_id": self.datasource_id,
            "dp_id": self.datapoint,
            "content": self.content
        }


class Batch(CommonModel):
    class Meta:
        verbose_name = _("annotation batch")
        verbose_name_plural = _("annotation batches")

    uuid = models.UUIDField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.uuid)


class Input(CommonModel):
    class Meta:
        verbose_name = _('input')
        verbose_name_plural = _('inputs')

    content = models.TextField(_("content"))
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, blank=True, null=True)
    context = models.ForeignKey(Context, on_delete=models.CASCADE, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(_("marker group order in the unit"), default=1, # TODO: rename
        help_text=_("At the submission time"))

    @property
    def hash(self):
        hash_gen = hashlib.sha256()
        hash_gen.update(self.content.encode('utf-8'))
        hash_gen.update(str(self.pk).encode("utf-8"))
        hash_gen.update(self.marker.code.encode('utf-8'))
        return hash_gen.hexdigest()

    @property
    def content_hash(self):
        return hash_text(self.content)

    def __str__(self):
        return truncate(self.content, 50)

    def to_minimal_json(self, dt_format=None):
        res = super(Input, self).to_json(dt_format=dt_format)
        res['content'] = self.content
        res['marker'] = self.marker.to_minimal_json()
        res['unit'] = self.unit
        return res

    def to_short_json(self, dt_format=None):
        res = super(Input, self).to_json(dt_format=dt_format)
        res['content'] = self.content
        res['marker'] = self.marker.to_json()
        res['user'] = self.batch.user.username
        res['batch'] = str(self.batch)
        res['unit'] = self.unit
        res['hash'] = self.hash
        return res

    def to_json(self, dt_format=None):
        res = self.to_short_json()
        res['context'] = self.context.content if self.context else None
        return res


class Label(CommonModel):
    class Meta:
        verbose_name = _('label')
        verbose_name_plural = _('labels')

    start = models.PositiveIntegerField(_("start position"), null=True,
        help_text=_("Character-wise start position in the text"))
    end = models.PositiveIntegerField(_("end position"), null=True,
        help_text=_("Character-wise end position in the text"))
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, null=True) # null is allowed for backward compatibility reason
    extra = models.JSONField(_("extra information"), null=True, blank=True,
        help_text=_("in a JSON format"))
    context = models.ForeignKey(Context, on_delete=models.CASCADE)
    undone = models.BooleanField(_("was undone?"), default=False,
        help_text=_("Indicates whether the annotator used 'Undo' button"))
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(_("marker group order in the unit"), default=1,
        help_text=_("At the submission time"))

    @property
    def hash(self):
        hash_gen = hashlib.sha256()
        hash_gen.update(self.text.encode('utf-8'))
        hash_gen.update(str(self.pk).encode("utf-8"))
        hash_gen.update(self.marker.code.encode('utf-8'))
        return hash_gen.hexdigest()

    @property
    def text(self):
        if self.start and self.end:
            return self.context.content[self.start:self.end] if self.context else ""
        else:
            return "{}<Text>".format(self.marker.name)

    def to_short_rel_json(self, dt_format=None):
        res = super(Label, self).to_json(dt_format=dt_format)
        res.update({
            'marker': self.marker.marker.name,
            'extra': self.extra,
            'start': self.start,
            'end': self.end,
            'text': self.text,
            'user': self.batch.user.username,
        })
        return res

    def to_rel_json(self, dt_format=None):
        res = self.to_short_rel_json()
        res['context'] = self.context.content
        return res

    def to_minimal_json(self, dt_format=None):
        res = self.to_short_rel_json()
        res['marker'] = self.marker.to_minimal_json()
        res['batch'] = str(self.batch)
        res['user'] = self.batch.user.username
        return res

    def to_short_json(self, dt_format=None):
        res = self.to_short_rel_json()
        res['marker'] = self.marker.to_json()
        res['batch'] = str(self.batch)
        res['user'] = self.batch.user.username
        res['hash'] = self.hash
        return res

    def to_json(self, dt_format=None):
        res = self.to_short_json()
        res['context'] = self.context.content
        return res

    def __str__(self):
        return self.text


class LabelReview(CommonModel):
    class Meta:
        verbose_name = _('label review')
        verbose_name_plural = _('label reviews')

    original = models.ForeignKey(Label, on_delete=models.CASCADE)
    is_match = models.BooleanField(_("is a match?"), null=True,
        help_text=_("Indicates whether the reviewed and original labels match"))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ambiguity_status = models.CharField(_("ambiguity?"), max_length=2, default='no',
        choices=[
            ('no', 'No ambiguity'), ('rr', 'Requires resolution'), ('rs', 'Resolved')
        ],
        help_text=_("Decided automatically to inform a decision maker"))
    resolved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='resolved_by')
    start = models.PositiveIntegerField(_("start position of the review label"), null=True,
        help_text=_("If applicable"))
    end = models.PositiveIntegerField(_("start position of the review label"), null=True,
        help_text=_("If applicable"))
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    impossible = models.BooleanField(_("is impossible?"), default=False,
        help_text=_("Indicates whether the reviewer marked the datapoint as impossible wrt. guidelines"))

    @property
    def text(self):
        return self.original.input.context.content[self.start:self.end]


class LabelRelation(CommonModel):
    class Meta:
        verbose_name = _('label relation')
        verbose_name_plural = _('label relations')

    rule = models.ForeignKey(Relation, on_delete=models.CASCADE)
    first_label = models.ForeignKey(Label, related_name='first_label', on_delete=models.CASCADE)
    second_label = models.ForeignKey(Label, related_name='second_label', on_delete=models.CASCADE)
    undone = models.BooleanField(_("was undone?"), default=False,
        help_text=_("Indicates whether the annotator used 'Undo' button"))
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(_("marker group order in the unit"), default=1,
        help_text=_("At the submission time"))

    @property
    def graph(self):
        return str(self)

    @property
    def label_ids(self):
        return [first_label.pk, second_label.pk]

    def __str__(self):
        if self.rule.direction == '0':
            return "{} --> {}".format(self.first_label.text, self.second_label.text)
        elif self.rule.direction == '1':
            return "{} <-- {}".format(self.first_label.text, self.second_label.text)
        else:
            return "{} --- {}".format(self.first_label.text, self.second_label.text)

    def to_short_json(self, dt_format=None):
        res = super(LabelRelation, self).to_json(dt_format=dt_format)
        res.update({
            'rule': self.rule.to_json(),
            'first': self.first_label.to_short_json(),
            'second': self.second_label.to_short_json(),
            'user': self.batch.user.username,
            'batch': str(self.batch)
        })
        return res

    def to_json(self, dt_format=None):
        res = super(LabelRelation, self).to_json(dt_format=dt_format)
        res.update({
            'rule': self.rule.to_json(),
            'first': self.first_label.to_json(),
            'second': self.second_label.to_json(),
            'user': self.batch.user.username,
            'batch': str(self.batch)
        })
        return res


class UserProfile(CommonModel):
    class Meta:
        verbose_name = _('a project-specific user profile')
        verbose_name_plural = _('project specific user profiles')

    points = models.FloatField(_("points in total"), default=0.0)
    asking_time = models.IntegerField(default=0) # total asking time [OBSOLETE]
    timed_questions = models.IntegerField(default=0) # might be that some questions were not timed (like the first bunch of questions) [OBSOLETE]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='participant_profiles')

    def level(self):
        return Level.objects.filter(points__lte=self.points).order_by("-number")[0]

    @property
    def aat(self):
        """
        Average asking time
        """
        return round(self.asking_time / self.timed_questions, 1) if self.asking_time > 0 and self.timed_questions > 0 else None

    @property
    def accepted(self):
        return LabelReview.objects.filter(original__user=self.user).count()

    @property
    def peer_points(self):
        return self.accepted / 2

    def reviewed(self):
        return LabelReview.objects.filter(user=self.user).count()

    def __str__(self):
        return self.user.username


class Level(CommonModel):
    class Meta:
        verbose_name = _('level')

    number = models.IntegerField()
    title = models.CharField(max_length=50)
    points = models.IntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)


