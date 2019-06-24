from django.contrib import admin
from django.contrib.auth.models import User, Permission
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


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    pass


admin.site.register(DataSource)
admin.site.register(Marker)
admin.site.register(Level)
