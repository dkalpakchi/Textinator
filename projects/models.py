import random
import re
import string
from datetime import datetime
from collections import defaultdict

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import caches
from django.utils import timezone

from tinymce import HTMLField
from filebrowser.fields import FileBrowseField

from .datasources import *
from .helpers import *


class CommonModel(models.Model):
    dt_created = models.DateTimeField(null=True, default=timezone.now, verbose_name="creation date")

    class Meta:
        abstract = True

    def to_json(self, dt_format=None):
        return {
            'created': self.dt_created.strftime(dt_format)
        } if dt_format else {}


class PostProcessingMethod(CommonModel):
    class Meta:
        verbose_name = 'Post-processing method'
        verbose_name_plural = 'Post-processing methods'

    name = models.CharField(max_length=50)
    helper = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# Create your models here.
class DataSource(CommonModel):
    name = models.CharField(max_length=50)
    source_type = models.CharField(max_length=10, choices=settings.DATASOURCE_TYPES)
    spec = models.TextField(null=False) # json spec of the data source
    post_processing_methods = models.ManyToManyField(PostProcessingMethod, blank=True)

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
        try:
            idp = int(idx)
        except:
            return None

        source_cls = DataSource.type2class(self.source_type)
        if source_cls:
            ds_instance = source_cls(self.spec.replace('\r\n', ' ').replace('\n', ' '))
        return ds_instance[idp]

    def size(self):
        source_cls = DataSource.type2class(self.source_type)
        ds_instance = source_cls(self.spec.replace('\r\n', ' ').replace('\n', ' '))
        return ds_instance.size()

    def __str__(self):
        return self.name


class MarkerAction(CommonModel):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=False)
    file = models.CharField(max_length=100)
    admin_filter = models.CharField(max_length=50, blank=True, null=True)

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
    name = models.CharField(max_length=50, unique=True)
    short = models.CharField(max_length=10, help_text='By default the capitalized first three character of the label', unique=True)
    color = models.CharField(max_length=10, choices=settings.MARKER_COLORS)
    for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True)
    shortcut = models.CharField(max_length=10, help_text="Keyboard shortcut for marking a piece of text with this label", null=True, blank=True)
    actions = models.ManyToManyField(MarkerAction, through='MarkerContextMenuItem', blank=True)

    def save(self, *args, **kwargs):
        if not self.short:
            self.short = self.name[:3].upper()
        super(Marker, self).save(*args, **kwargs)

    # TODO: should be count restrictions per project!
    def get_count_restrictions(self, stringify=True):
        try:
            restrictions = list(Marker.project_set.through.objects.filter(marker=self).all())
        except MarkerVariant.DoesNotExist:
            return ''
        return '&'.join([str(r) for r in restrictions]) if stringify else restrictions

    def is_part_of_relation(self):
        return bool(Relation.objects.filter(models.Q(pairs__first=self) | models.Q(pairs__second=self)).all())

    def __str__(self):
        return str(self.name)

    def to_json(self, dt_format=None):
        res = super(Marker, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name,
            'color': self.color,
            'short': self.short
        })
        return res


class MarkerContextMenuItem(CommonModel):
    action = models.ForeignKey(MarkerAction, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    verbose = models.CharField(max_length=50)
    verbose_admin = models.CharField(max_length=50, null=True, blank=True)
    field = models.CharField(max_length=50, null=True, blank=True)
    config = models.JSONField(null=True, blank=True)

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


class Project(CommonModel):
    title = models.CharField(max_length=50)
    short_description = models.TextField(max_length=1000, default="")
    institution = models.CharField(max_length=500, null=True, blank=True)
    supported_by = models.CharField(max_length=1000, null=True, blank=True)
    guidelines = HTMLField(null=True, blank=True)
    reminders = HTMLField(null=True, blank=True)
    temporary_message = HTMLField(null=True, blank=True)
    video_summary = FileBrowseField(max_length=1000, null=True, blank=True)
    sampling_with_replacement = models.BooleanField(default=False)
    disjoint_annotation = models.BooleanField(default=False)
    show_dataset_identifiers = models.BooleanField(default=False)
    # TODO: implement a context of a sentence
    # TODO: context size should depend on task_type (context is irrelevant for some tasks, e.g. text classification)
    # context size affects only labels, not inputs
    context_size = models.CharField(max_length=2, choices=[('no', 'No context'), ('t', 'Text'), ('p', 'Paragraph')],
        help_text="Context size for storing labels")
    task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES)
    dt_publish = models.DateTimeField(verbose_name="To be published at") # TODO: implement this functionality
    dt_finish = models.DateTimeField(verbose_name="To be finished at")   # TODO: implement this functionality
    dt_updated = models.DateTimeField(auto_now=True)
    collaborators = models.ManyToManyField(User, related_name='shared_projects', blank=True)
    participants = models.ManyToManyField(User, related_name='participations', through='UserProfile', blank=True)
    markers = models.ManyToManyField(Marker, through='MarkerVariant', blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    datasources = models.ManyToManyField(DataSource, through='ProjectData')
    is_open = models.BooleanField(default=False)
    is_peer_reviewed = models.BooleanField(default=False)
    allow_selecting_labels = models.BooleanField(default=False)
    disable_submitted_labels = models.BooleanField(default=True)
    max_markers_per_input = models.PositiveIntegerField(null=True, blank=True)
    round_length = models.PositiveIntegerField(null=True, blank=True, help_text="The number of text snippets consituting one round of the game")
    points_scope = models.CharField(max_length=2, choices=[('n', 'No points'), ('i', 'Per input'), ('l', 'Per label')],
        help_text="The scope of the submitted task")
    points_unit = models.PositiveIntegerField(default=1, help_text="Number of points per submitted task")
    has_intro_tour = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def relations(self):
        return Relation.objects.filter(models.Q(for_task_type=self.task_type) | models.Q(project=self)).all()

    def data(self, user):
        pdata = self.datasources.through.objects.filter(project=self).values_list('pk', flat=True)
        log = DataAccessLog.objects.filter(user=user, project_data__pk__in=pdata, is_submitted=False, is_skipped=False).first()
        print(log)
        if log:
            ds = log.project_data.datasource
            dp_id = log.datapoint
            return ds.postprocess(ds.get(dp_id)).strip(), dp_id, ds.name, ds.size(), ds.pk

        dp_taboo = defaultdict(set)
        if not self.sampling_with_replacement:
            pdata = self.datasources.through.objects.filter(project=self).values_list('pk', flat=True)
            if self.disjoint_annotation:
                # meaning each user annotates whatever is not annotated
                logs = DataAccessLog.objects.filter(project_data__pk__in=pdata).all()
            else:
                # meaning each user annotates all texts
                logs = DataAccessLog.objects.filter(project_data__pk__in=pdata, user=user).all()
            for log in logs:
                dp_taboo[log.project_data.datasource.pk].add(log.datapoint)

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

    def __str__(self):
        return self.title


class MarkerUnit(CommonModel):
    size = models.PositiveIntegerField(default=1)
    minimum_required = models.PositiveIntegerField(default=1)
    is_rankable = models.BooleanField(default=False)
    name = models.CharField(max_length=10, help_text="Internal name for the unit (max 10 characters)")

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.pk < other.pk


class MarkerVariant(CommonModel):
    class Meta:
        unique_together = (('project', 'marker', 'unit'),)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)    
    is_free_text = models.BooleanField(default=False)
    unit = models.ForeignKey(MarkerUnit, on_delete=models.CASCADE, blank=True, null=True)
    order_in_unit = models.PositiveIntegerField(blank=True, null=True)

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


    def to_json(self):
        res = self.marker.to_json()
        res['order'] = self.order_in_unit
        return res


class MarkerRestriction(CommonModel):
    variant = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE)
    kind = models.CharField(max_length=2, choices=[
        ('no', '-'), ('ls', '<'),
        ('le', '<='), ('gs', '>'),
        ('ge', '>='), ('eq', '=')
    ])
    value = models.PositiveIntegerField()

    def __str__(self):
        return self.kind + str(self.value)


class ProjectData(CommonModel):
    class Meta:
        unique_together = (('project', 'datasource'),)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE)


class DataAccessLog(CommonModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project_data = models.ForeignKey(ProjectData, on_delete=models.CASCADE)
    datapoint = models.CharField(max_length=64)
    flags = models.TextField(default="")
    is_submitted = models.BooleanField()
    is_skipped = models.BooleanField()


# TODO: put constraints on the markers - only markers belonging to project or task_type can be put!
# TODO: for one might want to mark pronouns 'det', 'den' iff they are really pronouns and not articles
#       maybe add a name of the boolean helper that lets you mark the word iff the helper returns true?
class PreMarker(CommonModel):
    class Meta:
        verbose_name = 'Pre-marker'
        verbose_name_plural = 'Pre-markers'
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    tokens = models.TextField(help_text="Comma-separated tokens that should be highlighted with a marker")


class MarkerPair(CommonModel):
    first = models.ForeignKey(Marker, related_name='first', on_delete=models.CASCADE)
    second = models.ForeignKey(Marker, related_name='second', on_delete=models.CASCADE)

    def __str__(self):
        return self.first.short + '-:-' + self.second.short


class Relation(CommonModel):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True)
    pairs = models.ManyToManyField(MarkerPair)
    direction = models.CharField(max_length=1, choices=[
        ('0', 'Directed from the first to the second'),
        ('1', 'Directed from the second to the first'),
        ('2', 'Bi-directional')
    ])
    shortcut = models.CharField(max_length=15, help_text="Keyboard shortcut for marking a piece of text with this label", null=True, blank=True)
    representation = models.CharField(max_length=1, choices=[('g', 'Graph'), ('l', 'List')], default='g',
                                      help_text="How the relation should be visualized?")

    @property
    def between(self):
        return "|".join([str(p) for p in self.pairs.all()])

    def __str__(self):
        return str(self.name)

    def to_json(self, dt_format=None):
        res = super(Relation, self).to_json(dt_format=dt_format)
        res.update({
            'name': self.name,
            'pairs': [str(p) for p in self.pairs.all()],
            'direction': self.direction
        })
        return res


# TODO: Add datapoint tracking
class Context(CommonModel):
    datasource = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()

    @property
    def content_hash(self):
        return hash_text(self.content)

    def save(self, *args, **kwargs):
        super(Context, self).save(*args, **kwargs)

    def __str__(self):
        return truncate(self.content)


class Batch(CommonModel):
    class Meta:
        verbose_name_plural = "Batches"

    uuid = models.UUIDField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.uuid)


class Input(CommonModel):
    content = models.TextField()
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, blank=True, null=True)
    context = models.ForeignKey(Context, on_delete=models.CASCADE, blank=True, null=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(default=1)

    @property
    def content_hash(self):
        return hash_text(self.content)

    def __str__(self):
        return truncate(self.content, 50)

    def to_short_json(self, dt_format=None):
        res = super(Input, self).to_json(dt_format=dt_format)
        res['content'] = self.content,
        res['marker'] = self.marker.to_json()
        res['user'] = self.batch.user.username
        res['batch'] = str(self.batch)
        return res

    def to_json(self, dt_format=None):
        res = self.to_short_json()
        res['context'] = self.context.content if self.context else None
        return res


class Label(CommonModel):
    start = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    marker = models.ForeignKey(MarkerVariant, on_delete=models.CASCADE, null=True) # null is allowed for backward compatibility reason
    extra = models.JSONField(null=True, blank=True)
    context = models.ForeignKey(Context, on_delete=models.CASCADE, null=True, blank=True) # if there is no input, there must be context
    undone = models.BooleanField(default=False)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(default=1)

    @property
    def text(self):
        return self.context.content[self.start:self.end] if self.context else ""

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
        res = super(Label, self).to_json(dt_format=dt_format)
        res.update(self.to_short_rel_json())
        res['context'] = self.context.content
        return res

    def to_short_json(self, dt_format=None):
        res = super(Label, self).to_json(dt_format=dt_format)
        res.update(self.to_short_rel_json())
        res['marker'] = self.marker.to_json()
        res['batch'] = str(self.batch)
        res['user'] = self.batch.user.username
        return res

    def to_json(self, dt_format=None):
        res = super(Label, self).to_json(dt_format=dt_format)
        res.update(self.to_short_json())
        res['context'] = self.context.content
        return res

    def __str__(self):
        return self.text


class LabelReview(CommonModel):
    original = models.ForeignKey(Label, on_delete=models.CASCADE)
    is_match = models.BooleanField(null=True) # whether the reviewed and original labels match (valid only if is_review=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ambiguity_status = models.CharField(max_length=2, default='no', choices=[
        ('no', 'No ambiguity'), ('rr', 'Requires resolution'), ('rs', 'Resolved')
    ])
    resolved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='resolved_by')
    start = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    impossible = models.BooleanField(default=False)

    @property
    def text(self):
        return self.original.input.context.content[self.start:self.end]


class LabelRelation(CommonModel):
    rule = models.ForeignKey(Relation, on_delete=models.CASCADE)
    first_label = models.ForeignKey(Label, related_name='first_label', on_delete=models.CASCADE)
    second_label = models.ForeignKey(Label, related_name='second_label', on_delete=models.CASCADE)
    undone = models.BooleanField(default=False)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True)
    unit = models.PositiveIntegerField(default=1)

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
    points = models.FloatField(default=0.0)
    asking_time = models.IntegerField(default=0) # total asking time
    timed_questions = models.IntegerField(default=0) # might be that some questions were not timed (like the first bunch of questions)
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
    number = models.IntegerField()
    title = models.CharField(max_length=50)
    points = models.IntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)


