# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models import Q
from django import forms
from django.conf import settings
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.template.loader import render_to_string

import nested_admin
# from modeltranslation.admin import TranslationAdmin
# from guardian.admin import GuardedModelAdmin

import projects.models as Tm
import projects.actions as Ta


class CommonModelAdmin(admin.ModelAdmin):
    readonly_fields = ['dt_created', 'dt_updated']
    _list_filter = []

    def changelist_view(self, request, extra_context=None):
        if not request.user.is_superuser:
            self.list_filter = []
        else:
            self.list_filter = self._list_filter
        return super(CommonModelAdmin, self).changelist_view(request, extra_context)


class CommonStackedInline(admin.StackedInline):
    readonly_fields = ['dt_created', 'dt_updated']


class CommonNestedStackedInline(nested_admin.NestedStackedInline):
    readonly_fields = ['dt_created', 'dt_updated']


class TextinatorJSONEditorWidget(forms.Widget):
    template_name = "admin/json_editor.html"

    def __init__(self, schema, field, collapsed=False, editor_options=None):
        super().__init__()
        # TODO: change theme to fit with the Admin's look & feel
        self.__field = field
        schema["options"] = {
            "collapsed": int(collapsed),
            "expand_height": 1
        }
        self.__editor_options = {
            "theme": "spectre",
            "schema": schema,
        }
        self.__editor_options.update(editor_options or {})

    def render(self, name, value, attrs=None, renderer=None):
        self.__editor_options["schema"]["title"] = " " # To emulate removed title
        return render_to_string(self.template_name, {
            "field": self.__field,
            "name": name,
            "value": value,
            "editor_options": self.__editor_options
        })

    @property
    def media(self):
        js = [
            '/{}static/@json-editor/json-editor/dist/jsoneditor.js'.format(settings.ROOT_URLPATH),
            '/{}static/scripts/admin_json_editor.js'.format(settings.ROOT_URLPATH)
        ]
        return forms.Media(js=js)


class MarkerRestrictionInline(CommonNestedStackedInline):
    model = Tm.MarkerRestriction
    extra = 0
    # classes = ['collapse']
    verbose_name = _("restriction")
    verbose_name_plural = _("restrictions")


class MarkerContextMenuItemInline(CommonNestedStackedInline):
    model = Tm.MarkerContextMenuItem
    verbose_name = _("context menu item")
    verbose_name_plural = _("context menu items")
    extra = 0
    exclude = ('verbose_admin',)


class MarkerVariantForm(forms.ModelForm):
    class Meta:
        model = Tm.MarkerVariant
        exclude = ('custom_suggestion_endpoint', 'are_suggestions_enabled',)
        DATA_SCHEMA = {
            "type": "array",
            "items": {
                "oneOf": [
                    {
                        "type": "string",
                        "format": "textarea"
                    },
                    {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "format": "textarea"
                        }
                    }
                ]
            }
        }
        widgets = {
            'choices': TextinatorJSONEditorWidget(DATA_SCHEMA, "choices", collapsed=True),
        }


class MarkerVariantInlineFormset(nested_admin.formsets.NestedInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(MarkerVariantInlineFormset, self).__init__(*args, **kwargs)

        for i in range(len(self.forms)):
            if self.forms[i].fields.get("custom_color"):
                # this takes care of assignment from parent model
                self.forms[i].initial["custom_color"] = self.forms[i].instance.color

            if self.forms[i].fields.get("custom_suggestion_endpoint"):
                # this takes care of assignment from parent model
                self.forms[i].initial["custom_suggestion_endpoint"] = self.forms[i].instance.suggestion_endpoint

            if self.forms[i].fields.get("custom_shortcut"):
                # this takes care of assignment from parent model
                self.forms[i].initial["custom_shortcut"] = self.forms[i].instance.shortcut


# TODO: fix name 'ModelValidationError' is not defined
#       happens when trying to assign marker to be both task and project specific
class MarkerVariantInline(CommonNestedStackedInline):
    model = Tm.MarkerVariant
    form = MarkerVariantForm
    formset = MarkerVariantInlineFormset
    extra = 0
    inlines = [MarkerRestrictionInline, MarkerContextMenuItemInline]
    verbose_name = _("project-specific marker")
    verbose_name_plural = _("project-specific markers")
    exclude = ('custom_suggestion_endpoint', 'are_suggestions_enabled',)
    ordering = ('display_tab', 'order_in_unit',)


class PreMarkerInline(CommonNestedStackedInline):
    model = Tm.PreMarker
    extra = 0


class UserProfileInline(CommonNestedStackedInline):
    model = Tm.UserProfile
    verbose_name = _("participant")
    verbose_name_plural = _("participants")
    extra = 0
    exclude = ('points', 'asking_time', 'timed_questions')


class LabelInline(CommonStackedInline):
    raw_id_fields = ('context', 'revision_of')
    readonly_fields = CommonStackedInline.readonly_fields + ['text']
    model = Tm.Label
    extra = 0


class BatchInline(CommonStackedInline):
    show_change_link = True
    verbose_name = _("revision")
    verbose_name_plural = _("revisions")
    raw_id_fields = ('revision_of',)
    readonly_fields = CommonStackedInline.readonly_fields
    model = Tm.Batch
    extra = 0


class RelationVariantInlineFormset(nested_admin.formsets.NestedInlineFormSet):
    model = Tm.RelationVariant

    def __init__(self, *args, **kwargs):
        super(RelationVariantInlineFormset, self).__init__(*args, **kwargs)

        for i in range(len(self.forms)):
            if self.forms[i].fields.get("custom_representation"):
                # this takes care of assignment from parent model
                self.forms[i].initial["custom_representation"] = self.forms[i].instance.representation

            if self.forms[i].fields.get("custom_shortcut"):
                # this takes care of assignment from parent model
                self.forms[i].initial["custom_shortcut"] = self.forms[i].instance.shortcut


class RelationVariantInline(CommonNestedStackedInline):
    model = Tm.RelationVariant
    formset = RelationVariantInlineFormset
    extra = 0
    verbose_name = _("project-specific relation")
    verbose_name_plural = _("project-specific relations")


class InputInline(CommonStackedInline):
    raw_id_fields = ('context', 'batch', 'marker', 'revision_of')
    model = Tm.Input
    extra = 0


class LabelRelationInline(CommonStackedInline):
    raw_id_fields = ('first_label', 'second_label')
    model = Tm.LabelRelation
    extra = 0


class ProjectForm(forms.ModelForm):
    datasources = forms.ModelMultipleChoiceField(
        queryset=None, # set later
        label=Tm.DataSource._meta.verbose_name_plural)

    class Meta:
        model = Tm.Project

        fields = [
            'title', 'language', 'short_description', 'institution', 'supported_by',
            'temporary_message', 'reminders', 'dt_publish', 'dt_finish', 'collaborators',
            'task_type', 'guidelines', 'video_summary', 'datasources', 'show_datasource_identifiers',
            'is_open', 'is_peer_reviewed', 'allow_selecting_labels', 'disable_submitted_labels',
            'disjoint_annotation', 'auto_text_switch', 'data_order', 'modal_configs'
            #'max_markers_per_input', 'has_intro_tour', 'round_length', 'points_scope', 'points_unit'
        ]
        widgets = {
                'modal_configs': TextinatorJSONEditorWidget({"type": "object"}, "modal_configs", collapsed=True),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.user.is_superuser:
            self.fields["datasources"].queryset = Tm.DataSource.objects.all()
        else:
            self.fields["datasources"].queryset = Tm.DataSource.objects.filter(
                Q(is_public=True) | Q(owner=self.user)
            )

    def clean_datasources(self):
        project_language = self.cleaned_data['language']
        sent_ds = self.cleaned_data['datasources']

        for ds in sent_ds:
            if ds.language != project_language:
                raise forms.ValidationError(_("All data sources must be of the same language as the project"))

        return sent_ds

    def save(self, commit=True):
        sent_ds = set(self.cleaned_data.pop('datasources'))

        instance = forms.ModelForm.save(self, commit=False)
        instance.save()
        try:
            project = Tm.Project.objects.get(pk=instance.pk)
            existing_ds = set(project.datasources.all())
        except Tm.Project.DoesNotExist:
            existing_ds = set()

        for ds in (existing_ds | sent_ds):
            if ds in existing_ds:
                if ds not in sent_ds:
                    # remove DS
                    project.datasources.remove(ds)
            else:
                project.datasources.add(ds)

        if instance._original_task_type != instance.task_type:
            self.mv2del = list(Tm.MarkerVariant.objects.filter(project=instance).values_list('pk', flat=True))
            self.rv2del = list(Tm.RelationVariant.objects.filter(project=instance).values_list('pk', flat=True))

            try:
                spec_obj = Tm.TaskTypeSpecification.objects.get(task_type=instance.task_type)
                spec = spec_obj.config
                marker_map = {}
                for mspec in spec["markers"]:
                    m = Tm.Marker.objects.get(pk=mspec["id"])
                    if mspec.get("unit_id"):
                        mv, is_created = Tm.MarkerVariant.objects.get_or_create(
                            marker=m, project=instance, anno_type=mspec["anno_type"], unit_id=mspec["unit_id"]
                        )
                    else:
                        mv, is_created = Tm.MarkerVariant.objects.get_or_create(marker=m, project=instance, anno_type=mspec["anno_type"])

                    if not is_created:
                        self.mv2del.remove(mv.pk)

                    if mspec.get("restrictions"):
                        mv.add_restrictions(mspec["restrictions"])
                    marker_map[mspec["id"]] = mv

                for rel_id in spec.get("relations", []):
                    r = Tm.Relation.objects.get(pk=rel_id)
                    Tm.RelationVariant.objects.create(relation=r, project=instance)

                for aspec in spec.get("actions", []):
                    aspec["action"] = Tm.MarkerAction.objects.get(name=aspec["name"])
                    aspec["marker"] = marker_map[aspec["marker_id"]]
                    del aspec["name"]
                    del aspec["marker_id"]
                    Tm.MarkerContextMenuItem.objects.get_or_create(**aspec)

            except Tm.TaskTypeSpecification.DoesNotExist:
                pass

        if instance.task_type == 'corr' or instance.task_type == 'pronr':
            instance.allow_selecting_labels = True

        self.save_m2m()
        instance.save()
        return instance



@admin.register(Tm.Project)
class ProjectAdmin(nested_admin.NestedModelAdmin):
    _list_filter = [
        'institution',
        'task_type',
        'is_open'
    ]
    fieldsets = (
        (None, {
            'fields': ('title', 'language', 'short_description', 'institution', 'supported_by',
                'dt_publish', 'dt_finish', 'collaborators', 'author')
        }),
        (_('task specification').title(), {
            'fields': ('task_type', 'guidelines', 'reminders', 'video_summary', 'modal_configs')
        }),
        (_('data').title(), {
            'fields': ('datasources', 'show_datasource_identifiers',)
        }),
        (_('settings').title(), {
            'fields': ('data_order', 'is_open', 'allow_selecting_labels', 'disable_submitted_labels',
                'disjoint_annotation', 'auto_text_switch', 'allow_editing', 'editing_as_revision', 'allow_reviewing', 'editing_title_regex')
        }),
        (_('administration').title(), {
            'fields': ('temporary_message',)
        }),
    )
    readonly_fields = ['dt_created', 'dt_updated', 'author']
    form = ProjectForm
    inlines = [MarkerVariantInline, RelationVariantInline, PreMarkerInline, UserProfileInline] #LevelInline, UserProfileInline]
    save_as = True
    exclude = ('is_peer_reviewed',)
    user_can_access_owned_objects_only = True
    user_owned_objects_field = 'author'
    actions = [Ta.clone_project]

    def get_form(self, request, *args, **kwargs):
        form = super(ProjectAdmin, self).get_form(request, *args, **kwargs)
        form.user = request.user
        return form

    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ProjectAdmin, self).save_related(request, form, formsets, change)

        if hasattr(form, 'mv2del'):
            Tm.MarkerVariant.objects.filter(pk__in=form.mv2del).delete()

        if hasattr(form, 'rv2del'):
            Tm.RelationVariant.objects.filter(pk__in=form.rv2del).delete()

    def changelist_view(self, request, extra_context=None):
        if not request.user.is_superuser:
            self.list_filter = []
        else:
            self.list_filter = self._list_filter
        return super(ProjectAdmin, self).changelist_view(request, extra_context)

    def view_on_site(self, obj):
        return reverse('projects:detail', kwargs={'pk': obj.pk})


@admin.register(Tm.Context)
class ContextAdmin(CommonModelAdmin):
    _list_filter = [
        'datasource'
    ]
    list_display = ['id', 'content']
    search_fields = ['content']
    inlines = [InputInline]
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash', 'id']


@admin.register(Tm.Input)
class InputAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['content_hash']
    # inlines = [LabelInline]
    list_display = ['content', 'context']
    search_fields = ['context__content', 'content']
    readonly_fields = CommonModelAdmin.readonly_fields + ['batch']
    raw_id_fields = ('revision_of',)


@admin.register(Tm.Batch)
class BatchAdmin(CommonModelAdmin):
    inlines = [InputInline, LabelInline, LabelRelationInline, BatchInline]
    search_fields = ['input__content', 'uuid']
    list_display = ['uuid', 'project', 'user']
    raw_id_fields = ('revision_of',)
    _list_filter = (
       'user',
    )


# TODO: translation?
# from django.utils.translation import ugettext_lazy as _

@admin.register(Tm.Label)
class LabelAdmin(CommonModelAdmin):
    _list_filter = (
       'marker',
       'batch__user',
       'marker__project',
       # ('dt_created', DateTimeRangeFilter),
       'undone'
    )
    readonly_fields = CommonModelAdmin.readonly_fields + ['text', 'batch']
    search_fields = ['context__content', 'batch__uuid']
    raw_id_fields = ('revision_of',)

    def get_queryset(self, request):
        qs = super(LabelAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(Tm.LabelRelation)
class LabelRelationAdmin(CommonModelAdmin):
    readonly_fields = CommonModelAdmin.readonly_fields + ['graph', 'batch']
    raw_id_fields = ('first_label', 'second_label')

    def get_queryset(self, request):
        qs = super(LabelRelationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# TODO: add autocomplete for data source specs
class DataSourceForm(forms.ModelForm):
    class Meta:
        model = Tm.DataSource
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
            'spec': TextinatorJSONEditorWidget(DATA_SCHEMA, "spec", collapsed=False),
        }


@admin.register(Tm.DataSource)
class DataSourceAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
        )

    form = DataSourceForm
    list_display = ['name', 'source_type']

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(Q(owner=request.user) | Q(is_public=True))

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_superuser:
            return readonly_fields
        else:
            return list(readonly_fields) + ['owner']

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tm.DataAccessLog)
class DataAccessLogAdmin(CommonModelAdmin):
    _list_filter = [
        'user',
        'project'
    ]
    list_display = ['id', 'user', 'project']


@admin.register(Tm.Marker)
class MarkerAdmin(CommonModelAdmin):
    exclude = ('suggestion_endpoint', 'code')

    def get_form(self, request, *args, **kwargs):
        form = super(MarkerAdmin, self).get_form(request, *args, **kwargs)

        if request.user.is_superuser:
            self.exclude = ['suggestion_endpoint']
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_superuser:
            return readonly_fields + ['code']
        return readonly_fields
    # def has_change_permission(request, obj=None)
    #     # Should return True if editing obj is permitted, False otherwise.
    #     # If obj is None, should return True or False to indicate whether editing of objects of this type is permitted in general

    # def has_delete_permission(request, obj=None)
    #     # Should return True if deleting obj is permitted, False otherwise.
    #     # If obj is None, should return True or False to indicate whether deleting objects of this type is permitted in general


@admin.register(Tm.Relation)
class RelationAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
            'scripts/shortcut_picker.js'
        )

# @admin.register(Level)
# class LevelAdmin(CommonModelAdmin): pass

@admin.register(Tm.PostProcessingMethod)
class PostProcessingMethodAdmin(CommonModelAdmin): pass

@admin.register(Tm.PreMarker)
class PreMarkerAdmin(CommonModelAdmin):
    user_can_access_owned_objects_only = True
    user_owned_objects_field = 'project__author'

@admin.register(Tm.MarkerPair)
class MarkerPairAdmin(CommonModelAdmin): pass

@admin.register(Tm.MarkerUnit)
class MarkerUnitAdmin(CommonModelAdmin): pass

@admin.register(Tm.Range)
class RangeAdmin(CommonModelAdmin): pass

class TaskTypeConfigForm(forms.ModelForm):
    class Meta:
        model = Tm.TaskTypeSpecification
        fields = '__all__'
        # TODO: fork django-admin-json-editor and make SQL syntax highlighting with AceEditor
        DATA_SCHEMA = {
            'type': 'object',
            "properties": {
                "markers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    }
                },
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    }
                }
            }
        }
        widgets = {
            'config': TextinatorJSONEditorWidget(DATA_SCHEMA, "config", collapsed=False),
        }

@admin.register(Tm.TaskTypeSpecification)
class TaskTypeSpecAdmin(CommonModelAdmin):
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery{}.js'.format('' if settings.DEBUG else '.min'),
        )

    form = TaskTypeConfigForm

admin.site.register(Permission)
admin.site.register(Tm.CeleryTask)
# admin.site.register(MarkerContextMenuItem)

admin.site.site_header = 'Textinator Admin'
admin.site.site_title = 'Textinator Admin'

admin.site.site_url = '/{}'.format(settings.ROOT_URLPATH)
