from django.db.models import Q
from projects.models import Project, UserProfile


def common_user_variables(request):
    if request.user.is_anonymous:
        return {}
    else:
        shared_projects = request.user.shared_projects.all()
        shared_ids = shared_projects.values_list('pk', flat=True)
        recently_shared, shared_before = [], []
        for p in shared_projects:
            if p.has_participant(request.user):
                shared_before.append(p)
            else:
                recently_shared.append(p)
        
        return {
            "open_projects": Project.objects.filter(
                is_open=True,
                language__in=request.user.profile.fluent_languages
            ).exclude(Q(participants__in=[request.user.id]) | Q(author=request.user)).all(),
            "user_projects": request.user.project_set.all(),
            "shared_before": shared_before,
            "recently_shared": recently_shared,
            'participations': request.user.participations.exclude(Q(author=request.user) | Q(pk__in=shared_ids)).all()
        }