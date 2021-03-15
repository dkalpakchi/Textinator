from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from django.db.models.fields import AutoField
from django import forms
from django.contrib.auth.models import User, Permission
from django_admin_json_editor import JSONEditorWidget
from django.contrib.admin import SimpleListFilter, DateFieldListFilter
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from .models import *


class CommonModelAdmin(admin.ModelAdmin):
    readonly_fields = ['dt_created']


# TODO: fix name 'ModelValidationError' is not defined
#       happens when trying to assign marker to be both task and project specific
class MarkerCountRestrictionInline(admin.StackedInline):
    model = MarkerCountRestriction
    extra = 0
    classes = ['collapse']
    verbose_name = "Project marker"
    verbose_name_plural = "Project markers"


class LevelInline(admin.StackedInline):
    model = Level
    extra = 0
    classes = ['collapse']


class PreMarkerInline(admin.StackedInline):
    model = PreMarker
    extra = 0
    classes = ['collapse']


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    verbose_name = "Participant"
    verbose_name_plural = "Participants"
    extra = 0
    classes = ['collapse']


class MarkerContextMenuItemInline(admin.StackedInline):
    model = MarkerContextMenuItem
    verbose_name = "Context menu item"
    verbose_name_plural = "Context menu items"
    extra = 0
    classes = ['collapse']


class LabelInline(admin.StackedInline):
    readonly_fields = ('text',)
    model = Label
    extra = 0
    classes = ['collapse']


class LabelReviewInline(admin.StackedInline):
    readonly_fields = ('text',)
    model = LabelReview
    extra = 0
    classes = ['collapse']


class RelationInline(admin.StackedInline):
    model = Relation
    extra = 0
    classes = ['collapse']
    verbose_name = "Project-specific relation"
    verbose_name_plural = "Project-specific relations"


class ProjectForm(forms.ModelForm):
    datasources = forms.ModelMultipleChoiceField(queryset=DataSource.objects.all())

    class Meta:
        model = Project
        fields = [
            'title', 'short_description', 'institution', 'supported_by', 'temporary_message', 'guidelines', 'reminders',
            'video_summary', 'sampling_with_replacement', 'context_size', 'task_type', 'dt_publish',
            'dt_finish', 'collaborators', 'author', 'datasources', 'is_open', 'is_peer_reviewed',
            'allow_selecting_labels', 'disable_submitted_labels', 'show_dataset_identifiers', 'max_markers_per_input',
            'round_length', 'points_scope', 'points_unit'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obj = kwargs.get('instance')
        if obj:
            source_ids = ProjectData.objects.filter(project=obj).values_list('datasource', flat=True)
            self.initial['datasources'] = source_ids

    def save(self, commit=True):
        sent_ds = set(self.cleaned_data.pop('datasources'))
        instance = forms.ModelForm.save(self, commit=False)
        
        try:
            project = Project.objects.get(pk=instance.pk)
            existing_ds = set(DataSource.objects.filter(pk__in=ProjectData.objects.filter(
                project=project).values_list('datasource', flat=True)).all())
        except Project.DoesNotExist:
            instance.save()
            existing_ds = set()

        for ds in (existing_ds | sent_ds):
            if ds in existing_ds:
                if ds not in sent_ds:
                    # remove DS
                    ProjectData.objects.get(project=project, datasource=ds).delete()
            else:
                ProjectData.objects.create(project=instance, datasource=ds)

        return instance


@admin.register(Project)
class ProjectAdmin(CommonModelAdmin):
    list_filter = [
        'institution',
        'task_type',
        'is_open'
    ]
    form = ProjectForm
    inlines = [MarkerCountRestrictionInline, RelationInline, PreMarkerInline, LevelInline, UserProfileInline]

    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ProjectAdmin, self).save_related(request, form, formsets, change)


@admin.register(Context)
class ContextAdmin(CommonModelAdmin):
    list_filter = [
        'datasource'
    ]
    list_display = ['id', 'content']
    search_fields = ['content']
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash', 'id']


@admin.register(Input)
class InputAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash']
    inlines = [LabelInline]
    list_display = ['content', 'context']
    search_fields = ['context__content', 'content']

# TODO: translation?
# from django.utils.translation import ugettext_lazy as _

@admin.register(Label)
class LabelAdmin(CommonModelAdmin):
    list_filter = (
       'marker',
       'user',
       'project',
       ('dt_created', DateTimeRangeFilter),
       'undone'
    )
    readonly_fields = CommonModelAdmin.readonly_fields + ['text', 'batch']
    inlines = [LabelReviewInline]
    search_fields = ['context__content', 'input__content']

    def get_queryset(self, request):
        qs = super(LabelAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(LabelReview)
class LabelReviewAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['text']

    def get_queryset(self, request):
        qs = super(LabelReviewAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(LabelRelation)
class LabelRelationAdmin(CommonModelAdmin):
    list_filter = [
        'project',
        'user'
    ]
    readonly_fields = CommonModelAdmin.readonly_fields + ['graph', 'batch']

    def get_queryset(self, request):
        qs = super(LabelRelationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# TODO: add autocomplete for data source specs
class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = '__all__'
        # TODO: fork django-admin-json-editor and make SQL syntax highlighting with AceEditor
        DATA_SCHEMA = {
            'type': 'object',
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "textarea"
                    }
                }
            }
        }
        widgets = {
            'spec': JSONEditorWidget(DATA_SCHEMA, collapsed=False),
        }


@admin.register(DataSource)
class DataSourceAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
            'scripts/datasource.js'
        )
    
    form = DataSourceForm
    list_display = ['name', 'source_type']


@admin.register(DataAccessLog)
class DataAccessLogAdmin(admin.ModelAdmin):
    list_filter = [
        'user'
    ]


@admin.register(Marker)
class MarkerAdmin(CommonModelAdmin):
    list_display = ['name', 'short', 'color']
    inlines = [MarkerContextMenuItemInline]

@admin.register(Relation)
class RelationAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
            'scripts/shortcut_picker.js'
        )

@admin.register(Level)
class LevelAdmin(CommonModelAdmin): pass

@admin.register(PostProcessingMethod)
class PostProcessingMethodAdmin(CommonModelAdmin): pass

@admin.register(PreMarker)
class PreMarkerAdmin(CommonModelAdmin): pass

admin.site.register(Permission)
admin.site.register(ProjectData)
admin.site.register(MarkerPair)
admin.site.register(MarkerAction)


admin.site.site_header = 'Textinator admin'
admin.site.site_title = 'Textinator admin'

admin.site.site_url = '/textinator'

