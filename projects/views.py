import json
import os
import random

from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.conf import settings
from django.template import Context, Template, RequestContext
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.cache import caches
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

import markdown

from .models import *
from .helpers import hash_text, retrieve_by_hash, get_new_article


# Create your views here.
class IndexView(LoginRequiredMixin, generic.ListView):
    model = Project
    template_name = 'projects/index.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['profiles'] = UserProfile.objects.filter(user=self.request.user).all()
        data['open_projects'] = Project.objects.filter(is_open=True).exclude(participants__in=[self.request.user]).all()
        return data



class DetailView(LoginRequiredMixin, PermissionRequiredMixin, generic.DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    permission_denied_message = 'you did not confirmed yet. please check your email.'

    def has_permission(self):
        return self.request.user.has_perm('projects.view_published_project')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        cache = caches['default']
        con = DetailView.context_object_name
        proj = data[con]

        task_markers = Marker.objects.filter(for_task_type=proj.task_type)

        ctx = {
            'text': get_new_article(proj),
            'project': proj,
            'task_markers': task_markers
        }

        if proj.author == self.request.user:
            ctx.update({
                'level': {'number': 3, 'points': 9, 'title': 'Hello world!'},
                'points': 10,
                'progress': 50,
                'next_level_points': 15,
                'leaderboard_template': render_to_string('projects/leaderboard.html', {
                    'user_profiles': json.load(open('projects/test_users.json')),
                    'user': {
                        'username': 'Johny'
                    }
                })
            })
        else:
            profile = get_object_or_404(UserProfile, user=self.request.user, project=proj)

            try:
                level = profile.level()
            except Level.DoesNotExist:
                raise Http404

            try:
                next_level = Level.objects.get(number=level.number + 1)

                if next_level:
                    next_level_points = next_level.points
                    if profile:
                        progress = round((profile.points - level.points) * 100 / (next_level.points - level.points))
                    else:
                        progress = 50
                else:
                    next_level_points = None
                    progress = None
            except Level.DoesNotExist:
                if proj.author == self.request.user:
                    next_level_points = 300
                    progress = 50
                else:
                    raise Http404
            
            ctx.update({
                'level': level,
                'points': profile.points if profile else 10,
                'progress': progress,
                'next_level_points': next_level_points,
                'leaderboard_template': render_to_string('projects/leaderboard.html', {
                    'user_profiles': UserProfile.objects.filter(project=proj).order_by('-points').all(),
                    'user': self.request.user
                })
            })

        with open(os.path.join(settings.BASE_DIR, proj.task_type, 'display.html')) as f:
            data['task_type_template'] = Template(f.read().replace('\n', '')).render(RequestContext(self.request, ctx))
        return data


@login_required
@require_http_methods(["POST"])
def record_datapoint(request):
    data = request.POST
    chunks = json.loads(data['chunks'])
    ctx_cache = caches['context']
    inp_cache = caches['input']

    user = request.user
    try:
        project = Project.objects.get(pk=data['pid'])
        u_profile = UserProfile.objects.get(user=user, project=project)
    except Project.DoesNotExist:
        raise Http404
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': True})

    for chunk in chunks:
        if chunk['marked']:
            if chunk['context']:
                ctx = retrieve_by_hash(chunk['context'], Context, ctx_cache)
                if not ctx:
                    ctx = Context.objects.create(content=chunk['context'])
                    ctx_cache.set(ctx.content_hash, ctx.pk, 600)
            else:
                ctx = None
            try:
                marker = Marker.objects.get(label_name=chunk['label'])
            except Marker.DoesNotExist:
                continue

            inp = retrieve_by_hash(data['question'], Input, inp_cache)
            if not inp:
                inp = Input.objects.create(context=ctx, project=project, content=data['question'])
                inp_cache.set(inp.content_hash, inp.pk, 600)
            lab = Label.objects.create(input=inp, start=chunk['lengthBefore'] + chunk['start'], end=chunk['lengthBefore'] + chunk['end'], marker=marker, user=user)
            u_profile.points += 1
    u_profile.save()
    level = u_profile.level()
    try:
        next_level = Level.objects.get(number=level.number + 1)
        next_level_points = next_level.points
    except Level.DoesNotExist:
        next_level_points = None
    print(level.number, level.points, next_level_points)
    return JsonResponse({
        'error': False,
        'points': u_profile.points,
        'level': level.number,
        'level_points': level.points,
        'next_level_points': next_level_points,
        'leaderboard_template': render_to_string('projects/leaderboard.html', {
            'user_profiles': UserProfile.objects.filter(project=project).order_by('-points').all(),
            'user': user
        })
    })


@login_required
@require_http_methods("POST")
def join_or_leave_project(request, proj):
    project = get_object_or_404(Project, pk=proj)
    current_user = request.user
    res = {
        'error': False,
        'result': ''
    }
    if project.participants.filter(pk=current_user.pk).exists():
        project.participants.remove(current_user)
        res['result'] = 'left'
    else:
        project.participants.add(current_user)
        res['result'] = 'joined'
    project.save()
    return JsonResponse(res)


@login_required
@require_http_methods("GET")
def profile(request, username):
    user = get_object_or_404(User, username=username)
    profiles = UserProfile.objects.filter(user=user).all()
    return render(request, 'projects/profile.html', {
        'total_participated': len(profiles),
        'total_points': sum(map(lambda x: x.points, profiles)),
        'user': user
    })


@login_required
@require_http_methods("POST")
def new_article(request, proj):
    project = Project.objects.get(pk=proj)
    return JsonResponse({
        'text': get_new_article(project)
    })


@login_required
@require_http_methods("GET")
def update_participations(request):
    n = request.GET.get('n', '')
    template = ''
    if n == 'p':
        open_projects = Project.objects.filter(is_open=True).exclude(participants__in=[request.user]).all()
        template = render_to_string('partials/_open_projects.html', {
            'open_projects': open_projects
        }, request=request)
    elif n == 'o':
        participations = request.user.participations.all()
        template = render_to_string('partials/_participations.html', {
            'participations': participations
        }, request=request)
        
    return JsonResponse({
        'template': template
    })
