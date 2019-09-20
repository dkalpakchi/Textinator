import random

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import caches
from django.utils import timezone

from .datasources import *
from .helpers import *

from dewiki.parser import Parser


class CommonModel(models.Model):
    dt_created = models.DateTimeField(null=True, default=timezone.now)

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


class Project(CommonModel):
    class Meta:
        permissions = [
            ("view_published_project", "View published project"),
        ]


    title = models.CharField(max_length=50)
    guideline = models.TextField(null=True)
    # TODO: implement a context of a sentence
    # TODO: context size should depend on task_type (context is irrelevant for some tasks, e.g. text classification)
    context_size = models.CharField(max_length=2, choices=[('no', 'No context'), ('t', 'Text'), ('p', 'Paragraph')])
    task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES)
    dt_publish = models.DateTimeField()
    dt_finish = models.DateTimeField()
    dt_updated = models.DateTimeField(auto_now=True)
    collaborators = models.ManyToManyField(User, related_name='shared_projects', blank=True)
    participants = models.ManyToManyField(User, related_name='participations', through='UserProfile', blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    datasources = models.ManyToManyField(DataSource)
    is_open = models.BooleanField(default=False)
    is_peer_reviewed = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def data(self):
        datasources = []
        for source in self.datasources.all():
            source_cls = DataSource.type2class(source.source_type)
            if source_cls:
                ds_instance = source_cls(source.spec.replace('\r\n', ' ').replace('\n', ' '))
                datasources.append((ds_instance, source.postprocess))

        # take a random data point from data
        nds = len(datasources)
        ds, postprocess = datasources[random.randint(0, nds - 1)]
        return postprocess(ds.get_random_datapoint())

    def get_profile_for(self, user):
        try:
            return UserProfile.objects.get(project=self, user=user)
        except UserProfile.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class Marker(CommonModel):
    name = models.CharField(max_length=50, unique=True)
    short = models.CharField(max_length=10, help_text='By default the capitalized first three character of the label', unique=True)
    color = models.CharField(max_length=10, choices=settings.MARKER_COLORS)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
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

    def __str__(self):
        return str(self.name)


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
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    @property
    def content_hash(self):
        return hash_text(self.content)

    def __str__(self):
        return truncate(self.content, 50)


class Label(CommonModel):
    start = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    input = models.ForeignKey(Input, on_delete=models.CASCADE, null=True)     # if input is there, input should be not NULL
    context = models.ForeignKey(Context, on_delete=models.CASCADE, null=True) # if there is no input, there must be context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    impossible = models.BooleanField(default=False)

    @property
    def text(self):
        if self.input:
            return self.input.context.content[self.start:self.end]
        else:
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
        return Input.objects.filter(user=self.user).count()

    def reviewed(self):
        return LabelReview.objects.filter(user=self.user).count()

    def __str__(self):
        return self.user.username


class Level(CommonModel):
    number = models.IntegerField()
    title = models.CharField(max_length=50)
    points = models.IntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)


