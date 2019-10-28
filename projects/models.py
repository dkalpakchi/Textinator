import random
import re
import string
from datetime import datetime

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import caches
from django.utils import timezone

from tinymce.models import HTMLField
from filebrowser.fields import FileBrowseField

from .datasources import *
from .helpers import *


class CommonModel(models.Model):
    dt_created = models.DateTimeField(null=True, default=timezone.now, verbose_name="Created at")

    class Meta:
        abstract = True


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

    def __str__(self):
        return self.name

class Marker(CommonModel):
    name = models.CharField(max_length=50, unique=True)
    short = models.CharField(max_length=10, help_text='By default the capitalized first three character of the label', unique=True)
    color = models.CharField(max_length=10, choices=settings.MARKER_COLORS)
    for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True)
    shortcut = models.CharField(max_length=10, help_text="Keyboard shortcut for marking a piece of text with this label", null=True, blank=True)

    def save(self, *args, **kwargs):
        if (self.project and self.for_task_type):
            raise ModelValidationError("The marker can be either project-specific or task-specific, not both")
        elif (not self.project and not self.for_task_type):
            raise ModelValidationError("The marker should be either project-specific or task-specific")
        else:
            if not self.short:
                self.short = self.name[:3].upper()
            super(Marker, self).save(*args, **kwargs)

    def get_count_restriction(self, stringify=False):
        try:
            obj = Marker.project_set.through.objects.filter(marker=self).get()
        except MarkerCountRestriction.DoesNotExist:
            return ''
        if obj.restriction_type != 'no':
            return str(obj) if stringify else obj 
        else:
            return ''

    def is_part_of_relation(self):
        return bool(Relation.objects.filter(models.Q(first_node=self) | models.Q(second_node=self)).all())


    def __str__(self):
        return str(self.name)

class Project(CommonModel):
    title = models.CharField(max_length=50)
    short_description = models.TextField(max_length=1000, default="")
    institution = models.CharField(max_length=500, null=True, blank=True)
    supported_by = models.CharField(max_length=1000, null=True, blank=True)
    guidelines = HTMLField(null=True, blank=True)
    reminders = HTMLField(null=True, blank=True)
    video_summary = FileBrowseField(max_length=1000, null=True, blank=True)
    # TODO: implement a context of a sentence
    # TODO: context size should depend on task_type (context is irrelevant for some tasks, e.g. text classification)
    context_size = models.CharField(max_length=2, choices=[('no', 'No context'), ('t', 'Text'), ('p', 'Paragraph')])
    task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES)
    dt_publish = models.DateTimeField(verbose_name="To be published at") # TODO: implement this functionality
    dt_finish = models.DateTimeField(verbose_name="To be finished at")   # TODO: implement this functionality
    dt_updated = models.DateTimeField(auto_now=True)
    collaborators = models.ManyToManyField(User, related_name='shared_projects', blank=True)
    participants = models.ManyToManyField(User, related_name='participations', through='UserProfile', blank=True)
    markers = models.ManyToManyField(Marker, through='MarkerCountRestriction', blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    datasources = models.ManyToManyField(DataSource)
    is_open = models.BooleanField(default=False)
    is_peer_reviewed = models.BooleanField(default=False)
    max_markers_per_input = models.PositiveIntegerField(null=True, blank=True)
    round_length = models.PositiveIntegerField(null=True, blank=True, help_text="The number of text snippets consituting one round of the game")
    points_scope = models.CharField(max_length=2, choices=[('n', 'No points'), ('i', 'Per input'), ('l', 'Per label')],
        help_text="The scope of the submitted task")
    points_unit = models.PositiveIntegerField(default=1, help_text="Number of points per submitted task")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def data(self):
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
        ds_ind = sum([priors_cumsum[i] <= rnd for i in range(len(priors_cumsum))]) - 1

        ds, postprocess, ids = datasources[ds_ind]

        # now choose a random datapoint from the chosen dataset and return a datasource id as well
        return postprocess(ds.get_random_datapoint()).strip(), ids

    def get_profile_for(self, user):
        try:
            return UserProfile.objects.get(project=self, user=user)
        except UserProfile.DoesNotExist:
            return None

    def has_participant(self, user):
        return user in self.participants.all()

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

class MarkerCountRestriction(CommonModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    restriction_type = models.CharField(max_length=2, choices=[('no', '-'), ('ls', '<'), ('le', '<='), ('gs', '>'), ('ge', '>=')], default='no')
    restriction_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.restriction_type + str(self.restriction_value)


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


class Relation(CommonModel):
    name = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True)
    first_node = models.ForeignKey(Marker, related_name="first_node", on_delete=models.CASCADE)
    second_node = models.ForeignKey(Marker, related_name="second_node", on_delete=models.CASCADE)
    direction = models.CharField(max_length=1, choices=[
        ('0', 'Directed from the first to the second'),
        ('1', 'Directed from the second to the first'),
        ('2', 'Bi-directional')
    ])

    @property
    def between(self):
        return self.first_node.short + '-:-' + self.second_node.short

    def __str__(self):
        return str(self.name)


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


class Input(CommonModel):
    content = models.TextField()
    context = models.ForeignKey(Context, on_delete=models.CASCADE, blank=True, null=True)

    @property
    def content_hash(self):
        return hash_text(self.content)

    def __str__(self):
        return truncate(self.content, 50)


class Label(CommonModel):
    start = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    input = models.ForeignKey(Input, on_delete=models.CASCADE, null=True, blank=True)     # if input is there, input should be not NULL
    context = models.ForeignKey(Context, on_delete=models.CASCADE, null=True, blank=True) # if there is no input, there must be context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    impossible = models.BooleanField(default=False)
    undone = models.BooleanField(default=False)
    batch = models.UUIDField(null=True)

    @property
    def text(self):
        return self.context.content[self.start:self.end]


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
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    undone = models.BooleanField(default=False)
    batch = models.UUIDField(null=True)

    @property
    def graph(self):
        return str(self)

    def __str__(self):
        if self.rule.direction == '0':
            return "{} --> {}".format(self.first_label.text, self.second_label.text)
        elif self.rule.direction == '1':
            return "{} <-- {}".format(self.first_label.text, self.second_label.text)
        else:
            return "{} --- {}".format(self.first_label.text, self.second_label.text)



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

    def submitted(self):
        k = self.project.points_unit
        if self.project.points_scope == 'i':
            return k * Label.objects.filter(user=self.user, project=self.project, undone=False).values_list('input_id').distinct().count()
        elif self.project.points_scope == 'l':
            return k * Label.objects.filter(user=self.user, project=self.project, undone=False).count()
        else:
            return -1

    def submitted_today(self):
        k, now = self.project.points_unit, datetime.now()
        if self.project.points_scope == 'i':
            return k * Label.objects.filter(
                user=self.user,
                project=self.project,
                dt_created__day=now.day,
                dt_created__month=now.month,
                dt_created__year=now.year,
                undone=False
            ).values_list('input_id').distinct().count()
        elif self.project.points_scope == 'l':
            return k * Label.objects.filter(
                user=self.user,
                project=self.project,
                dt_created__day=now.day,
                dt_created__month=now.month,
                dt_created__year=now.year,
                undone=False
            ).count()
        else:
            return -1
        

    def reviewed(self):
        return LabelReview.objects.filter(user=self.user).count()

    def __str__(self):
        return self.user.username


class Level(CommonModel):
    number = models.IntegerField()
    title = models.CharField(max_length=50)
    points = models.IntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)


