from django.contrib import admin
from django import forms
from django.contrib.auth.models import User, Permission
from django_admin_json_editor import JSONEditorWidget

from .models import *


class MarkerInline(admin.StackedInline):
    model = Marker
    extra = 0
    classes = ['collapse']


class LevelInline(admin.StackedInline):
    model = Level
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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [MarkerInline, LevelInline, UserProfileInline]

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(ProjectAdmin, self).save_related(request, form, formsets, change)
        proj_perm = 'view_published_project'
        perm = Permission.objects.get(codename=proj_perm)
        perm_users = User.objects.filter(user_permissions=perm).distinct()
        participants = form.instance.participants.all()
        collaborators = form.instance.collaborators.all()

        for u in perm_users:
            if u not in collaborators and u not in participants:
                u.user_permissions.remove(perm)

        for c in collaborators:
            c.user_permissions.add(perm)

        for p in participants:
            p.user_permissions.add(perm)


@admin.register(Context)
class ContextAdmin(admin.ModelAdmin):
    readonly_fields = ('content_hash',)


@admin.register(Input)
class InputAdmin(admin.ModelAdmin):
    readonly_fields = ('content_hash',)
    inlines = [LabelInline]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    readonly_fields = ('text',)
    inlines = [LabelReviewInline]


@admin.register(LabelReview)
class LabelReviewAdmin(admin.ModelAdmin):
    readonly_fields = ('text',)


@admin.register(LabelRelation)
class LabelRelationAdmin(admin.ModelAdmin):
    readonly_fields = ('graph',)


class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = '__all__'
        # TODO: fork django-admin-json-editor and make SQL syntax highlighting with AceEditor
        DATA_SCHEMA = {
            'type': 'object',
            'title': 'DataSource',
            'properties': {
                'rand_dp_query': {
                    'format': 'textarea',
                    'propertyOrder': 1001
                }
            },
        }
        widgets = {
            'spec': JSONEditorWidget(DATA_SCHEMA, collapsed=False),
        }


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    form = DataSourceForm


admin.site.register(Marker)
admin.site.register(Relation)
admin.site.register(Level)

admin.site.site_header = 'Textinator admin'
admin.site.site_title = 'Textinator admin'

