import json
import os
import random
import bisect
import uuid
from collections import defaultdict, OrderedDict

from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.conf import settings
from django.template import Context, RequestContext
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.cache import caches
from django.template.loader import render_to_string, get_template
from django.contrib.auth.decorators import login_required

from chartjs.views.columns import BaseColumnsHighChartsView
from chartjs.views.lines import BaseLineChartView

from .models import *
from .helpers import hash_text, retrieve_by_hash, apply_premarkers
from .view_helpers import process_chunk
from .exporters import *

from Textinator.jinja2 import prettify

##
## Chart views
##

class LabelLengthJSONView(BaseColumnsHighChartsView):
    title = "Label lengths"
    yUnit = "labels"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        self.labels = Label.objects.filter(project__id=self.pk, undone=False).all()
        self.x_axis = sorted(set([len(l.text.split()) for l in self.labels]))
        self.project = Project.objects.get(pk=self.pk)
        self.participants = self.project.participants.all()
        return self.x_axis

    def get_providers(self):
        """Return names of datasets."""
        return [m.name for m in self.project.markers.all()]

    def get_data(self):
        """Return 3 datasets to plot."""
        data = [[0] * len(self.x_axis) for _ in range(len(self.project.markers.all()))]
        self.l2i = {v: k for k, v in enumerate(self.x_axis)}
        self.p2i = {v.name: k for k, v in enumerate(self.project.markers.all())}

        for l in self.labels:
            try:
                data[self.p2i[l.marker.name]][self.l2i[len(l.text.split())]] += 1
            except:
                pass
        return data

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        data = super(LabelLengthJSONView, self).get_context_data(**kwargs)
        return data

label_lengths_chart_json = LabelLengthJSONView.as_view()


class UserTimingJSONView(BaseColumnsHighChartsView):
    title = "User timing, in minutes"
    yUnit = "items"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        labels = Label.objects.filter(project__id=self.pk, undone=False).order_by('dt_created').all()
        self.labels_by_user = defaultdict(list)
        for l in labels:
            self.labels_by_user[l.user.username].append(l)

        timings = []
        for u in self.labels_by_user:
            ll = self.labels_by_user[u]
            for l1, l2 in zip(ll[:len(ll)], ll[1:]):
                if l1 and l2 and l1.dt_created and l2.dt_created:
                    timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1) # in minutes
                    if timing < 60:
                        timings.append(timing)
        if timings:
            min_time, max_time = int(min(timings)), int(round(max(timings)))
            self.x_axis = list(range(min_time, max_time, 1))
            self.x_axis.append(self.x_axis[-1] + 1)

            self.project = Project.objects.get(pk=self.pk)
            self.participants = self.project.participants.all()
            return ["{} - {}".format(t1, t2) for t1, t2 in zip(self.x_axis[:-1], self.x_axis[1:])]
        else:
            return []

    def get_providers(self):
        """Return names of datasets."""
        if hasattr(self, 'participants'):
            return [p.username for p in self.participants]
        else:
            return []

    def get_data(self):
        """Return 3 datasets to plot."""
        if hasattr(self, 'participants'):
            data = [[0] * len(self.x_axis) for _ in range(len(self.participants))]
            self.p2i = {v.username: k for k, v in enumerate(self.participants)}

            for u in self.labels_by_user:
                ll = self.labels_by_user[u]
                for l1, l2 in zip(ll[:len(ll)], ll[1:]):
                    try:
                        if l1 and l2 and l1.dt_created and l2.dt_created:
                            timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1)
                            if timing < 60:
                                pos = bisect.bisect(self.x_axis, timing)
                                data[self.p2i[u]][pos - 1] += 1
                    except:
                        pass
            return data
        else:
            return []

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        data = super(UserTimingJSONView, self).get_context_data(**kwargs)
        return data

user_timing_chart_json = UserTimingJSONView.as_view()


##
## Page views
##

# Create your views here.
class IndexView(LoginRequiredMixin, generic.ListView):
    model = Project
    template_name = 'projects/index.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['profiles'] = UserProfile.objects.filter(user=self.request.user).all()
        data['open_projects'] = Project.objects.filter(is_open=True).exclude(participants__in=[self.request.user]).all()
        return data


class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    permission_denied_message = 'you did not confirmed yet. please check your email.'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        cache = caches['default']
        con = DetailView.context_object_name
        proj = data[con]

        u = self.request.user
        if not proj.has_participant(u): raise Http404

        task_markers = Marker.objects.filter(for_task_type=proj.task_type)
        task_relations = Relation.objects.filter(for_task_type=proj.task_type)

        u_profile = UserProfile.objects.filter(user=u, project=proj).get()

        dp, dp_id, source_size, source_id = proj.data(u)

        logs = None
        if source_id != -1:
            try:
                p_data = ProjectData.objects.get(project=proj, datasource=DataSource.objects.get(pk=source_id))
                logs = DataAccessLog.objects.filter(user=u, project_data=p_data).count()
            except DataSource.DoesNotExist:
                print("DataSource does not exist")
                pass
            except DataAccessLog.DoesNotExist:
                print("DataAccessLog does not exist")
                pass
            except ProjectData.DoesNotExist:
                print("ProjectData does not exist")
                pass

        ctx = {
            'text': apply_premarkers(proj, dp),
            'source_id': source_id,
            'source_size':  source_size,
            'dp_id': dp_id,
            'source_finished': logs + 1 >= source_size if logs else False,
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

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)
        except Http404:
            return redirect('projects:join_or_leave', proj=self.object.pk)


@login_required
@require_http_methods(["POST"])
def record_datapoint(request, proj):
    data = request.POST
    chunks = json.loads(data['chunks'])
    relations = json.loads(data['relations'])
    ctx_cache, inp_cache = caches['context'], caches['input']

    is_review = data.get('is_review', 'f') == 'true'
    is_resolution = data.get('is_resolution', 'f') == 'true'

    batch = uuid.uuid4()

    user = request.user
    try:
        project = Project.objects.get(pk=proj)
        u_profile = UserProfile.objects.get(user=user, project=project)
        data_source = DataSource.objects.get(pk=data['datasource'])

        if not project.sampling_with_replacement:
            project_data = ProjectData.objects.get(project=project, datasource=data_source)
            DataAccessLog.objects.create(user=user, project_data=project_data, datapoint=str(data['datapoint']))
    except Project.DoesNotExist:
        raise Http404
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': True})
    except DataSource.DoesNotExist:
        data_source = None

    # First create a chunk for a input context (if available), which is always all text
    if 'input_context' in data and type(data['input_context']) == str:
        ctx = retrieve_by_hash(data['input_context'], Context, ctx_cache)
        if not ctx:
            ctx = Context.objects.create(datasource=data_source, content=data['input_context'])
            ctx_cache.set(ctx.content_hash, ctx.pk, 3600)
    else:
        ctx = None

    # Next create an input for that context if available
    # We will have one input, no matter what, but can have many labels for it
    if data.get('input'):
        inp = retrieve_by_hash(data['input'], Input, inp_cache)
        if not inp:
            inp = Input.objects.create(context=ctx, content=data['input'])
            inp_cache.set(inp.content_hash, inp.pk, 600)
    else:
        inp = None

    saved_labels = 0
    label_cache = {}
    for chunk in chunks:
        # inp is typically the same for all chunks
        ret_caches, inp, just_saved = process_chunk(chunk, batch, inp, project, data_source, user, (ctx_cache, inp_cache, label_cache), (is_resolution, is_review))
        ctx_cache, inp_cache, label_cache = ret_caches
        saved_labels += just_saved

    for rel in relations:
        source_id, target_id = int(rel['s']), int(rel['t'])

        try:
            source_label = Label.objects.filter(pk=label_cache.get(source_id, -1)).get()
            target_label = Label.objects.filter(pk=label_cache.get(target_id, -1)).get()
        except Label.DoesNotExist:
            continue

        try:
            rule = Relation.objects.filter(pk=rel['rule']).get()
        except Relation.DoesNotExist:
            continue

        LabelRelation.objects.create(rule=rule, first_label=source_label, second_label=target_label, user=user, project=project, batch=batch)

    # Peer review task
    # if project.is_peer_reviewed:
    #     if u_profile.submitted() > 5 and random.random() > 0.5:
    #         inp_query = Input.objects.exclude(user=user).values('pk')
    #         rand_inp_id = random.choice(inp_query)['pk']
    #         inp = Input.objects.get(pk=rand_inp_id)
    #     else:
    #         inp = None
    # else:
    #     inp = None

    return JsonResponse({
        'error': False,
        'input': {
            'content': inp.content,
            'context': inp.context.content
        } if inp else None,
        'submitted': u_profile.submitted(),
        'submitted_today': u_profile.submitted_today(),
        'next_task': 'regular'
    })


@login_required
@require_http_methods(["GET", "POST"])
def join_or_leave_project(request, proj):
    project = get_object_or_404(Project, pk=proj)
    current_user = request.user
    if request.method == "POST":
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

        if request.POST.get('n', 'p') == 'j':
            # if from a join page
            return redirect('projects:detail', pk=project.pk)
        else:
            return JsonResponse(res)
    else:
        if project.participants.filter(pk=current_user.pk).exists():
            return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            return render(request, 'projects/join.html', {
                'project': project
            })


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


# TODO: fix error that sometimes happens -- PayloadTooLargeError: request entity too large
@login_required
@require_http_methods("POST")
def new_article(request, proj):
    project = Project.objects.get(pk=proj)
    dp, dp_id, source_size, source_id = project.data(request.user)
    return JsonResponse({
        'text': prettify(apply_premarkers(project, dp)),
        'source_id': source_id,
        'source_size':  source_size,
        'dp_id': dp_id
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


@login_required
@require_http_methods("POST")
def undo_last(request, proj):
    user = request.user
    project = Project.objects.get(pk=proj)

    try:
        u_profile = UserProfile.objects.get(user=user, project=project)
    except UserProfile.DoesNotExist:
        u_profile = None

    # find a last relation submitted if any
    rel_batch = LabelRelation.objects.filter(user=user, project=project).order_by('-dt_created').all()[:1].values('batch')
    last_rels = LabelRelation.objects.filter(batch__in=rel_batch).all()
    
    label_batch = Label.objects.filter(user=user, project=project).order_by('-dt_created').all()[:1].values('batch')
    last_labels = Label.objects.filter(batch__in=label_batch).all()
    
    labels = []
    last_input = ''

    if last_rels and last_labels:
        max_rel_dt_created = max(map(lambda x: x.dt_created, last_rels))
        max_lab_dt_created = max(map(lambda x: x.dt_created, last_labels))
        if max_rel_dt_created > max_lab_dt_created:
            # means relation was the latest
            for last_rel in last_rels:
                last_rel.first_label.undone = True
                last_rel.first_label.save()
                labels.append(last_rel.first_label.text)

                last_rel.second_label.undone = True
                last_rel.second_label.save()
                labels.append(last_rel.second_label.text)

                last_rel.undone = True
                last_rel.save()

            if last_rel.second_label.input:
                last_input = last_rel.second_label.input.content
        else:
            # means the label was the latest
            for last_label in last_labels:
                last_label.undone = True
                last_label.save()
                labels.append(last_label.text)
            if last_label.input:
                last_input = last_label.input.content
    elif last_labels:
        for last_label in last_labels:
            last_label.undone = True
            last_label.save()
            labels.append(last_label.text)
        if last_label.input:
            last_input = last_label.input.content

    return JsonResponse({
        'error': False,
        'labels': labels,
        'input': last_input,
        'submitted': u_profile.submitted() if u_profile else 'NA',
        'submitted_today': u_profile.submitted_today() if u_profile else 'NA'
    })


@login_required
def data_explorer(request, proj):
    if request.user.is_staff:
        project = Project.objects.filter(pk=proj).get()

        if project.task_type == 'qa':
            inputs_pks = Label.objects.filter(project=project, undone=False).values_list('input', flat=True).distinct()
            inputs = Input.objects.filter(pk__in=inputs_pks).order_by('-dt_created').all()
            labeled_inputs = [
                (inp, Label.objects.filter(input=inp, undone=False).all())
                for inp in inputs
            ]
            return render(request, 'projects/data_explorer.html', {
                'project': project,
                'labeled_inputs': labeled_inputs
            })
        elif project.task_type == 'corr':
            label_relations = LabelRelation.objects.filter(project=project, undone=False).order_by('-dt_created')

            relations = OrderedDict()
            for lr in label_relations:
                fst, snd = lr.first_label, lr.second_label
                if fst.context.pk in relations:
                    relations[fst.context.pk].append((fst, snd))
                else:
                    relations[fst.context.pk] = [(fst, snd)]

            return render(request, 'projects/data_explorer.html', {
                'project': project,
                'relations': [
                    (Context.objects.get(pk=cpk), rels)
                    for cpk, rels in relations.items()
                ]
            })
    else:
        raise Http404


@login_required
@require_http_methods(["POST"])
def async_delete_input(request, proj, inp):
    try:
        Input.objects.filter(pk=inp).delete()
    except:
        pass
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_http_methods(["GET"])
def export(request, proj):
    project = Project.objects.filter(pk=proj).get()
    task_type = project.task_type
    exporter = globals().get('export_{}'.format(task_type))
    if exporter:
        return JsonResponse({"data": exporter(project)})
    else:
        raise Http404