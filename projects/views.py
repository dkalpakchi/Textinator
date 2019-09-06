import json
import os
import random

from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.conf import settings
from django.template import Context, RequestContext
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.cache import caches
from django.template.loader import render_to_string, get_template
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
        task_relations = Relation.objects.filter(for_task_type=proj.task_type)

        u_profile = UserProfile.objects.filter(user=self.request.user, project=proj).get()

        ctx = {
            'text': proj.data(), #get_new_article(proj),
            'project': proj,
            'task_markers': task_markers,
            'task_relations': task_relations,
            'profile': u_profile
        }

        tmpl = get_template(os.path.join(proj.task_type, 'display.html'))
        data['task_type_template'] = tmpl.render(ctx, self.request)

        # with open(os.path.join(settings.BASE_DIR, proj.task_type, 'display.html')) as f:
        #     tmpl = Template(f.read().replace('\n', ''))
        return data


@login_required
@require_http_methods(["POST"])
def record_datapoint(request):
    data = request.POST
    chunks = json.loads(data['chunks'])
    relations = json.loads(data['relations'])
    ctx_cache, inp_cache = caches['context'], caches['input']

    print(relations)

    is_review = data.get('is_review', 'f') == 'true'
    is_resolution = data.get('is_resolution', 'f') == 'true'

    user = request.user
    try:
        project = Project.objects.get(pk=data['pid'])
        u_profile = UserProfile.objects.get(user=user, project=project)
    except Project.DoesNotExist:
        raise Http404
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': True})

    saved_labels = 0
    for chunk in chunks:
        if chunk.get('marked', False):
            if 'context' in chunk and type(chunk['context']) == str:
                ctx = retrieve_by_hash(chunk['context'], Context, ctx_cache)
                if not ctx:
                    ctx = Context.objects.create(content=chunk['context'])
                    ctx_cache.set(ctx.content_hash, ctx.pk, 600)
            else:
                ctx = None

            try:
                if (not 'label' in chunk) or (type(chunk['label']) != str): continue
                marker = Marker.objects.get(name=chunk['label'].strip())
            except Marker.DoesNotExist:
                continue

            if 'input' in data:
                inp = retrieve_by_hash(data['input'], Input, inp_cache)
                if not inp:
                    inp = Input.objects.create(context=ctx, project=project, content=data['input'], user=user)
                    inp_cache.set(inp.content_hash, inp.pk, 600)
            else:
                inp = None

            if 'lengthBefore' in chunk and 'start' in chunk and 'end' in chunk:
                new_start = chunk['lengthBefore'] + chunk['start']
                new_end = chunk['lengthBefore'] + chunk['end']

                if is_resolution:
                    # resolution case
                    pass
                elif is_review:
                    # check if matches original answer
                    if inp:
                        original = Label.objects.filter(input=inp).get()
                    else:
                        original = Label.objects.filter(context=ctx).get()

                    if original:
                        ambiguity_status, is_match = 'no', False
                        no_overlap = (original.start > new_end) or (original.end < new_start)
                        
                        if not no_overlap:
                            is_match = (original.start == new_start) and (original.end == new_end)
                            if not is_match:
                                requires_resolution = (original.start == new_start) or (original.end == new_end)
                                if requires_resolution:
                                    ambiguity_status = 'rr'
                        
                        LabelReview.objects.create(
                            original=original, start=new_start, end=new_end, user=user, marker=marker,
                            ambiguity_status=ambiguity_status, is_match=is_match
                        )
                else:
                    if inp:
                        Label.objects.create(
                            input=inp, start=new_start, end=new_end, marker=marker, user=user
                        )
                    else:
                        Label.objects.create(
                            context=ctx, start=new_start, end=new_end, marker=marker, user=user
                        )
                    saved_labels += 1

    # TODO: after dealing with chunks, deal with relations by finding the necessary Labels
    #       and put those specified in the relations to LabelRelations.
    
    if saved_labels > 0:
        # means the user has provided at least one new input
        u_profile.points += 0.5 # asking points
        if 'time' in data:
            u_profile.asking_time += float(data['time'])
            u_profile.timed_questions += 1
    u_profile.save()

    if project.is_peer_reviewed:
        if u_profile.submitted() > 5 and random.random() > 0.5:
            inp_query = Input.objects.exclude(user=user).values('pk')
            rand_inp_id = random.choice(inp_query)['pk']
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
        } if inp else None,
        'aat': u_profile.aat,
        'inp_points': u_profile.points,
        'peer_points': u_profile.peer_points
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
