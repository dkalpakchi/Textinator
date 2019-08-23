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
            'task_markers': task_markers,
            'guidelines': render_to_string('partials/_guidelines.html', {
                'project': proj
            })
        }

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

    is_review = data['is_review'] == 'true'

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
                inp = Input.objects.create(context=ctx, project=project, content=data['question'], user=user)
                inp_cache.set(inp.content_hash, inp.pk, 600)

            new_start = chunk['lengthBefore'] + chunk['start']
            new_end = chunk['lengthBefore'] + chunk['end']

            if is_review:
                # check if matches original answer
                original = Label.objects.filter(input=inp, is_review=False).get()
                if original:
                    is_match = (original.start == new_start) and (original.end == new_end)
                else:
                    is_match = False
            else:
                is_match = None

            lab = Label.objects.create(input=inp, start=new_start, end=new_end, marker=marker,
                user=user, is_review=is_review, is_match=is_match)
            u_profile.points += 1
    u_profile.save()

    if project.is_peer_reviewed:
        print(u_profile.submitted())
        if u_profile.submitted() > 5:
            inp_query = Input.objects.exclude(user=user).values('pk')
            rand_inp_id = random.choice(inp_query.all())['pk']
            inp = Input.objects.get(pk=rand_inp_id)
        else:
            inp = None
    else:
        inp = None

    return JsonResponse({
        'error': False,
        'input': {
            'content': inp.content,
            'context': inp.context.content
        } if inp else None
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
