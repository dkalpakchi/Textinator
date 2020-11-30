from projects.models import Project, UserProfile


def common_user_variables(request):
    data = {
        "open_projects": Project.objects.filter(is_open=True).exclude(participants__in=[request.user.id]).all(),
        "shared_projects": request.user.shared_projects.all(),
        "user_projects": request.user.project_set.all(),
    }
    # participations, which are not shared
    data['participations'] = Project.objects.filter(pk__in=UserProfile.objects.filter(user=request.user)\
        .exclude(project__in=data['shared_projects']).values_list('project', flat=True).distinct()).all()
    data["newly_shared"] = [p for p in data["shared_projects"] if not p.has_participant(request.user)]
    return data