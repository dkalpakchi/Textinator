from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from django.db.models.fields import AutoField
from django import forms
from django.contrib.auth.models import User, Permission
from django_admin_json_editor import JSONEditorWidget
from django.contrib.admin import SimpleListFilter, DateFieldListFilter
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

import nested_admin

from .models import *


class CommonModelAdmin(admin.ModelAdmin):
    readonly_fields = ['dt_created']
    _list_filter = []

    def changelist_view(self, request, extra_context=None):    
        if not request.user.is_superuser:
            self.list_filter = []
        else:
            self.list_filter = self._list_filter
        return super(CommonModelAdmin, self).changelist_view(request, extra_context)


class MarkerRestrictionInline(nested_admin.NestedStackedInline):
    model = MarkerRestriction
    extra = 0
    # classes = ['collapse']
    verbose_name = "Restriction"
    verbose_name_plural = "Restrictions"


# TODO: fix name 'ModelValidationError' is not defined
#       happens when trying to assign marker to be both task and project specific
class MarkerVariantInline(nested_admin.NestedStackedInline):
    model = MarkerVariant
    extra = 0
    inlines = [MarkerRestrictionInline]
    verbose_name = "Project marker"
    verbose_name_plural = "Project markers"


class LevelInline(nested_admin.NestedStackedInline):
    model = Level
    extra = 0


class PreMarkerInline(nested_admin.NestedStackedInline):
    model = PreMarker
    extra = 0


class UserProfileInline(nested_admin.NestedStackedInline):
    model = UserProfile
    verbose_name = "Participant"
    verbose_name_plural = "Participants"
    extra = 0


class MarkerContextMenuItemInline(admin.StackedInline):
    model = MarkerContextMenuItem
    verbose_name = "Context menu item"
    verbose_name_plural = "Context menu items"
    extra = 0


class LabelInline(admin.StackedInline):
    readonly_fields = ('text',)
    model = Label
    extra = 0

class LabelReviewInline(admin.StackedInline):
    readonly_fields = ('text',)
    model = LabelReview
    extra = 0


class RelationInline(nested_admin.NestedStackedInline):
    model = Relation
    extra = 0
    verbose_name = "Project-specific relation"
    verbose_name_plural = "Project-specific relations"


class InputInline(admin.StackedInline):
    model = Input
    extra = 0


class LabelRelationInline(admin.StackedInline):
    raw_id_fields = ('first_label', 'second_label')
    model = LabelRelation
    extra = 0



class ProjectForm(forms.ModelForm):
    datasources = forms.ModelMultipleChoiceField(queryset=DataSource.objects.all())

    class Meta:
        model = Project
        fields = [
            'title', 'short_description', 'institution', 'supported_by', 'temporary_message', 'guidelines', 'reminders',
            'video_summary', 'sampling_with_replacement', 'disjoint_annotation', 'context_size', 'task_type', 'dt_publish',
            'dt_finish', 'collaborators', 'author', 'datasources', 'is_open', 'is_peer_reviewed',
            'allow_selecting_labels', 'disable_submitted_labels', 'show_dataset_identifiers', 'has_intro_tour', 'max_markers_per_input',
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
class ProjectAdmin(nested_admin.NestedModelAdmin):
    _list_filter = [
        'institution',
        'task_type',
        'is_open'
    ]
    readonly_fields = ['dt_created']
    form = ProjectForm
    inlines = [MarkerVariantInline, RelationInline, PreMarkerInline, LevelInline, UserProfileInline]
    save_as = True

    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ProjectAdmin, self).save_related(request, form, formsets, change)

    def changelist_view(self, request, extra_context=None):    
        if not request.user.is_superuser:
            self.list_filter = []
        else:
            self.list_filter = self._list_filter
        return super(ProjectAdmin, self).changelist_view(request, extra_context)


@admin.register(Context)
class ContextAdmin(CommonModelAdmin):
    _list_filter = [
        'datasource'
    ]
    list_display = ['id', 'content']
    search_fields = ['content']
    inlines = [InputInline]
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash', 'id']


@admin.register(Input)
class InputAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash']
    # inlines = [LabelInline]
    list_display = ['content', 'context']
    search_fields = ['context__content', 'content']
    readonly_fields = CommonModelAdmin.readonly_fields + ['batch']


@admin.register(Batch)
class BatchAdmin(CommonModelAdmin):
    inlines = [InputInline, LabelInline, LabelRelationInline]
    search_fields = ['input__content', 'uuid']
    list_display = ['uuid', 'user']


# TODO: translation?
# from django.utils.translation import ugettext_lazy as _

@admin.register(Label)
class LabelAdmin(CommonModelAdmin):
    _list_filter = (
       'marker',
       'batch__user',
       'marker__project',
       ('dt_created', DateTimeRangeFilter),
       'undone'
    )
    readonly_fields = CommonModelAdmin.readonly_fields + ['text', 'batch']
    inlines = [LabelReviewInline]
    search_fields = ['context__content', 'batch__uuid']

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
    _list_filter = [
        'project',
        'user'
    ]
    readonly_fields = CommonModelAdmin.readonly_fields + ['graph', 'batch']
    raw_id_fields = ('first_label', 'second_label')

    def get_queryset(self, request):
        qs = super(LabelRelationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


class TextinatorJSONEditorWidget(JSONEditorWidget):
    @property
    def media(self):
        css = {
            'all': [
                'django_admin_json_editor/fontawesome/css/font-awesome.min.css',
                'django_admin_json_editor/style.css',
            ]
        }
        js = [
            'django_admin_json_editor/jsoneditor/jsoneditor.min.js',
        ]

        if self._sceditor:
            css['all'].append('django_admin_json_editor/sceditor/themes/default.min.css')
            js.append('django_admin_json_editor/sceditor/jquery.sceditor.bbcode.min.js')
        return forms.Media(css=css, js=js)


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
            'spec': TextinatorJSONEditorWidget(DATA_SCHEMA, collapsed=False),
        }


@admin.register(DataSource)
class DataSourceAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
        )
    
    form = DataSourceForm
    list_display = ['name', 'source_type']


@admin.register(DataAccessLog)
class DataAccessLogAdmin(CommonModelAdmin):
    _list_filter = [
        'user',
        'project_data__project'
    ]


@admin.register(Marker)
class MarkerAdmin(CommonModelAdmin):
    list_display = ['name', 'short', 'color']
    inlines = [MarkerContextMenuItemInline]

    regular_user_fields = ['name', 'short', 'color', 'shortcut']
    admin_user_fields = ['for_task_type']

    def get_fields(self, request, obj=None):
        """
        Hook for specifying fields.
        """
        self.fields = self.regular_user_fields
        if request.user.is_superuser:
            # INVESTIGATE: if using += on self.fields, the fields are accumulated for some reason
            self.fields = self.regular_user_fields + self.admin_user_fields
        return self.fields


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
admin.site.register(MarkerUnit)
admin.site.register(MarkerRestriction)


admin.site.site_header = 'Textinator admin'
admin.site.site_title = 'Textinator admin'

admin.site.site_url = '/textinator'

