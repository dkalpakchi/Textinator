import random

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import caches

from .datasources import *
from .helpers import hash_text, truncate

from dewiki.parser import Parser


# Create your models here.
class DataSource(models.Model):
    name = models.CharField(max_length=50)
    source_type = models.CharField(max_length=10, choices=settings.DATASOURCE_TYPES)
    spec = models.TextField(null=False) # json spec of the data source

    @classmethod
    def type2class(cls, source_type):
        return globals().get(source_type + 'Source')

    def __str__(self):
        return self.name


class Project(models.Model):
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
                datasources.append(ds_instance)

        # take a random data point from data
        nds = len(datasources)
        ds = datasources[random.randint(0, nds - 1)]
        return ds.get_random_datapoint()

    def get_profile_for(self, user):
        try:
            return UserProfile.objects.get(project=self, user=user)
        except UserProfile.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        
        super(Project, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class Marker(models.Model):
    label_name = models.CharField(max_length=50, unique=True)
    short = models.CharField(max_length=10, help_text='By default the capitalized first three character of the label', blank=True, null=True)
    color = models.CharField(max_length=10, choices=settings.MARKER_COLORS)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True)
    for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True)

    def save(self, *args, **kwargs):
        if (self.project and self.for_task_type):
            raise ModelValidationError("The marker can be either project-specific or task-specific, not both")
        elif (not self.project and not self.for_task_type):
            raise ModelValidationError("The marker should be either project-specific or task-specific")
        else:
            if not self.short:
                self.short = self.label_name[:3].upper()
            super(Marker, self).save(*args, **kwargs) 

    def __str__(self):
        return str(self.label_name)


class Context(models.Model):
    content = models.TextField()

    @property
    def content_hash(self):
        return hash_text(self.content)

    def save(self, *args, **kwargs):
        super(Context, self).save(*args, **kwargs)

    def __str__(self):
        return truncate(self.content)


class Input(models.Model):
    content = models.TextField()
    context = models.ForeignKey(Context, on_delete=models.CASCADE, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    @property
    def content_hash(self):
        return hash_text(self.content)

    def __str__(self):
        return truncate(self.content, 50)


class Label(models.Model):
    start = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    marker = models.ForeignKey(Marker, on_delete=models.CASCADE)
    input = models.ForeignKey(Input, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_review = models.BooleanField(default=False)
    is_match = models.BooleanField(null=True) # whether the reviewed and original labels match (valid only if is_review=True)
    impossible = models.BooleanField(default=False)

    @property
    def text(self):
        return self.input.context.content[self.start:self.end]


class UserProfile(models.Model):
    points = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='participant_profiles')

    def level(self):
        return Level.objects.filter(points__lte=self.points).order_by("-number")[0]

    # def discarded(self):
    #     Label.objects.filter(is_review=True, input__user=self.user).values('input').annotate(discarded=models.Count('is_match') - models.Sum('is_match'))

    def submitted(self):
        return Input.objects.filter(user=self.user).count()

    def reviewed(self):
        return Label.objects.filter(user=self.user, is_review=True).exclude(input__user=self.user).count()

    def __str__(self):
        return self.user.username


class Level(models.Model):
    number = models.IntegerField()
    title = models.CharField(max_length=50)
    points = models.IntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

