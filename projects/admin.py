from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from django.db.models.fields import AutoField
from django import forms
from django.contrib.auth.models import User, Permission
from django_admin_json_editor import JSONEditorWidget
from django.contrib.admin import SimpleListFilter

from .models import *


class CommonModelAdmin(admin.ModelAdmin):
    readonly_fields = ['dt_created']


# TODO: fix name 'ModelValidationError' is not defined
#       happens when trying to assign marker to be both task and project specific
class MarkerCountRestrictionInline(admin.StackedInline):
    model = MarkerCountRestriction
    extra = 0
    classes = ['collapse']
    verbose_name = "Project-specific marker"
    verbose_name_plural = "Project-specific markers"


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


@admin.register(Project)
class ProjectAdmin(CommonModelAdmin):
    inlines = [MarkerCountRestrictionInline, RelationInline, PreMarkerInline, LevelInline, UserProfileInline]

    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ProjectAdmin, self).save_related(request, form, formsets, change)


@admin.register(Context)
class ContextAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash']


@admin.register(Input)
class InputAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash']
    inlines = [LabelInline]

# TODO: translation?
# from django.utils.translation import ugettext_lazy as _

@admin.register(Label)
class LabelAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['text', 'batch']
    inlines = [LabelReviewInline]

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
        js = ('scripts/datasource.js',)
    
    form = DataSourceForm


@admin.register(Marker)
class MarkerAdmin(CommonModelAdmin): pass

@admin.register(Relation)
class RelationAdmin(CommonModelAdmin): pass

@admin.register(Level)
class LevelAdmin(CommonModelAdmin): pass

@admin.register(PostProcessingMethod)
class PostProcessingMethodAdmin(CommonModelAdmin): pass

@admin.register(PreMarker)
class PreMarkerAdmin(CommonModelAdmin): pass

admin.site.register(Permission)

admin.site.site_header = 'Textinator admin'
admin.site.site_title = 'Textinator admin'

admin.site.site_url = '/textinator'

