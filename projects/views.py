import os
import importlib
import random

from django.http import JsonResponse
from django.shortcuts import render
from django.views import generic
from django.conf import settings
from django.template import Context, Template, RequestContext
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.cache import caches

from .models import *
from .helpers import hash_text, retrieve_by_hash

# for k, v in settings.TASK_TYPES:
#     globals()[k] = importlib.import_module(k)


# Create your views here.
class IndexView(generic.ListView):
    model = Project
    template_name = 'projects/index.html'
    context_object_name = 'project_list'

    def get_queryset(self):
        """Return the last five published questions."""
        return Project.objects.filter(author=self.request.user)


class DetailView(PermissionRequiredMixin, generic.DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    permission_denied_message = 'you did not confirmed yet. please check your email.'

    def has_permission(self):
        return self.request.user.has_perm('projects.view_published_project')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        con = DetailView.context_object_name
        proj = data[con]

        task_markers = Marker.objects.filter(for_task_type=proj.task_type)

        # Get data
        ds = proj.data()[0]
        ctx = {
            'text': ds[1],#random.randint(0, 4)],
            'project': proj,
            'task_markers': task_markers

        }
        with open(os.path.join(settings.BASE_DIR, proj.task_type, 'display.html')) as f:
            data['task_type_template'] = Template(f.read().replace('\n', '')).render(RequestContext(self.request, ctx))
        return data


@require_http_methods(["POST"])
def record_datapoint(request):
    data = request.POST
    chunks = json.loads(data['chunks'])
    ctx_cache = caches['context']
    inp_cache = caches['input']

    user = request.user
    project = Project.objects.get(pk=data['pid'])
    u_profile = UserProfile.objects.get(user=user, project=project)

    if u_profile:
        ctx = retrieve_by_hash(data['context'], Context, ctx_cache)
        if not ctx:
            ctx = Context.objects.create(content=data['context'])
            ctx_cache.set(ctx.content_hash, ctx.pk, 600)

        for chunk in chunks:
            if chunk['marked']:
                inp = retrieve_by_hash(data['question'], Input, inp_cache)
                if not inp:
                    inp = Input.objects.create(context=ctx, content=data['question'])
                    inp_cache.set(inp.content_hash, inp.pk, 600)
                marker = Marker.objects.get(label_name=chunk['label'])
                lab = Label.objects.create(input=inp, start=chunk['start'], end=chunk['end'], marker=marker)
                u_profile.points += 1
        u_profile.save()
        level = u_profile.level()
        prev_level_points = Level.objects.get(number=level.number - 1).points
        return JsonResponse({'points': u_profile.points, 'level': level.number, 'prev_level_points': prev_level_points})
    else:
        return JsonResponse({})



