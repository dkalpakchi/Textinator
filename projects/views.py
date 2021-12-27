import json
import os
import io
import random
import bisect
import uuid
from collections import defaultdict, OrderedDict
from itertools import chain

from django.http import JsonResponse, Http404, HttpResponse, FileResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.conf import settings
from django.template import Context, RequestContext
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.core.cache import caches
from django.template.loader import render_to_string, get_template
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from chartjs.views.columns import BaseColumnsHighChartsView
from chartjs.views.lines import BaseLineChartView

from modeltranslation.translator import translator

from .models import *
from .helpers import hash_text, retrieve_by_hash, apply_premarkers
from .view_helpers import process_chunk
from .exporters import *

from Textinator.jinja2 import prettify


PT2MM = 0.3527777778
MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December']

##
## Chart views
##

class LabelLengthJSONView(BaseColumnsHighChartsView):
    title = "Label/input lengths (words)"
    yUnit = "labels/inputs"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        self.labels = Label.objects.filter(marker__project__id=self.pk, undone=False).all()
        self.inputs = Input.objects.filter(marker__project__id=self.pk).all()
        self.x_axis = sorted(set([len(l.text.split()) for l in self.labels]) | set([len(i.content.split()) for i in self.inputs]))
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

        for source in [self.labels, self.inputs]:
            for l in source:
                try:
                    data[self.p2i[l.marker.marker.name]][self.l2i[len(l.text.split())]] += 1
                except:
                    try:
                        data[self.p2i[l.marker.marker.name]][self.l2i[len(l.content.split())]] += 1
                    except:
                        pass
        return data

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        data = super(LabelLengthJSONView, self).get_context_data(**kwargs)
        return data

label_lengths_chart_json = LabelLengthJSONView.as_view()


class UserTimingJSONView(BaseColumnsHighChartsView):
    title = "User timing (minutes)"
    yUnit = "batches"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        inputs = Input.objects.filter(marker__project__id=self.pk).order_by('dt_created').all()
        labels = Label.objects.filter(marker__project__id=self.pk, undone=False).order_by('dt_created').all()
        self.inputs_by_user = defaultdict(lambda: defaultdict(list))
        self.labels_by_user = defaultdict(lambda: defaultdict(list))
        for i in inputs:
            self.inputs_by_user[i.batch.user.username][str(i.batch)].append(i)
        for l in labels:
            self.labels_by_user[l.batch.user.username][str(l.batch)].append(l)

        timings = []
        for arr in [self.inputs_by_user, self.labels_by_user]:
            for u in arr:
                ll = list(arr[u].items())
                for b1, b2 in zip(ll[:len(ll)], ll[1:]):
                    l1, l2 = b1[1][0], b2[1][0]
                    if l1 and l2 and l1.dt_created and l2.dt_created and l1.dt_created.month == l2.dt_created.month and\
                        l1.dt_created.day == l2.dt_created.day and l1.dt_created.year == l2.dt_created.year:
                        timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1) # in minutes
                        if timing > 0 and timing < 120:
                            # if timing is 0, means they were simply a part of the same batch
                            # timing < 60 is simply a precaution
                            timings.append(timing)

        if timings:
            min_time, max_time = int(min(timings)), int(round(max(timings)))
            self.x_axis = list(range(min_time, max_time, 1))
            if self.x_axis:
                self.x_axis.append(self.x_axis[-1] + 1)

            self.project = Project.objects.get(pk=self.pk)
            self.participants = self.project.participants.all()
            return self.x_axis
        else:
            return []

    def get_providers(self):
        """Return names of datasets."""
        if hasattr(self, 'participants'):
            return [p.username for p in self.participants]
        else:
            return []

    def get_data(self):
        if hasattr(self, 'participants'):
            data = [[0] * len(self.x_axis) for _ in range(len(self.participants))]
            self.p2i = {v.username: k for k, v in enumerate(self.participants)}

            for arr in [self.inputs_by_user, self.labels_by_user]:
                for u in arr:
                    ll = list(arr[u].items())
                    for b1, b2 in zip(ll[:len(ll)], ll[1:]):                            
                        try:
                            l1, l2 = b1[1][0], b2[1][0]
                            if l1 and l2 and l1.dt_created and l2.dt_created:
                                timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1)
                                if timing > 0 and timing < 120:
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


class UserProgressJSONView(BaseColumnsHighChartsView):
    title = "Progress (%)"
    yUnit = "%"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        project_data = ProjectData.objects.filter(project__id=self.pk).values('pk')
        logs = DataAccessLog.objects.filter(project_data__id__in=project_data)
        submitted_logs = logs.filter(is_submitted=True)
        skipped_logs = logs.filter(is_skipped=True)
        
        self.submitted_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.skipped_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.dataset_info = {}
        self.l2i, i = {}, 0
        for logs_data, logs_storage in zip(
            [submitted_logs, skipped_logs], 
            [self.submitted_logs_by_ds_and_user, self.skipped_logs_by_ds_and_user]):
            for l in logs_data:
                ds = l.project_data.datasource
                logs_storage[ds.pk][l.user.pk][l.datapoint].append(l)
                self.dataset_info[ds.pk] = {
                    'size': ds.size(),
                    'name': ds.name
                }
                if ds.pk not in self.l2i:
                    self.l2i[ds.pk] = i
                    i += 1
        self.x_axis = [self.dataset_info[k]['name'] for k in self.dataset_info]

        self.project = Project.objects.get(pk=self.pk)
        self.participants = self.project.participants.all()
        
        return self.x_axis

    def get_series(self):
        """Generate HighCharts series from providers and data."""
        series = []
        data = self.get_data()
        providers = self.get_providers()
        for i, d in enumerate(data):
            series.append({"name": providers[i] + '_submitted', "data": d[0], 'stack': providers[i]})
            series.append({"name": providers[i] + '_skipped', "data": d[1], 'stack': providers[i]})
        return series

    def get_providers(self):
        """Return names of datasets."""
        if hasattr(self, 'participants'):
            return [p.username for p in self.participants]
        else:
            return []

    def get_data(self):
        """Return 3 datasets to plot."""
        if hasattr(self, 'participants'):
            data = [[[0] * len(self.x_axis), [0] * len(self.x_axis)] for _ in range(len(self.participants))]
            self.p2i = {v.pk: k for k, v in enumerate(self.participants)}

            for logs_data, stack in zip([self.submitted_logs_by_ds_and_user, self.skipped_logs_by_ds_and_user], ['submitted', 'skipped']):
                for ds in logs_data:
                    ds_logs = logs_data[ds]
                    for u in ds_logs:
                        if stack == 'submitted':
                            data[self.p2i[u]][0][self.l2i[ds]] = round(len(ds_logs[u].keys()) * 100 / self.dataset_info[ds]['size'], 2)
                        else:
                            data[self.p2i[u]][1][self.l2i[ds]] = round(len(ds_logs[u].keys()) * 100 / self.dataset_info[ds]['size'], 2)
            return data
        else:
            return []

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        data = super(UserProgressJSONView, self).get_context_data(**kwargs)
        y = self.get_yAxis()
        y["max"] = 100
        opt = self.get_plotOptions()
        opt["column"]["stacking"] = "normal"
        data.update({
            "yAxis": y,
            "plotOptions": opt
        })
        return data

user_progress_chart_json = UserProgressJSONView.as_view()


class DataSourceSizeJSONView(BaseColumnsHighChartsView):
    title = "Data source sizes (texts)"
    yUnit = "texts"

    def get_labels(self):
        """Return 7 labels for the x-axis."""
        self.project = Project.objects.get(pk=self.pk)
        self.x_axis = list(self.project.datasources.values_list('name', flat=True))
        return self.x_axis

    def get_providers(self):
        # set visible: false in JS
        return [0]

    def get_data(self):
        """Return 3 datasets to plot."""
        return [[p.size() for p in self.project.datasources.all()]]

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        data = super(DataSourceSizeJSONView, self).get_context_data(**kwargs)
        return data

datasource_size_chart_json = DataSourceSizeJSONView.as_view()

##
## Page views
##

# This could potentially be converted into a function view?
class IndexView(LoginRequiredMixin, generic.ListView):
    model = Project
    template_name = 'projects/index.html'


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

        fallback_languages = (proj.language, u.profile.preferred_language, 'en')
        Marker.name.fallback_languages = {'default': fallback_languages}
        Relation.name.fallback_languages = {'default': fallback_languages}

        # TODO:
        # This is supposed to be an equivalent solution to the above, but
        # results in `{{ no such element: projects.models.Marker object['name'] }}`
        # in the template, investigate, since this will be needed if we are to
        # translate more fields for more models.
        #
        # for model in translator.get_registered_models():
        #     if model._meta.app_label == Project._meta.app_label:
        #         opts = translator.get_options_for_model(model)
        #         for field_name in opts.fields:
        #             descriptor = getattr(model, field_name)
        #             setattr(descriptor, 'fallback_languages', fallback_languages)

        u_profile = UserProfile.objects.filter(user=u, project=proj).get()

        dp, dp_id, dp_source_name, source_size, source_id = proj.data(u)

        logs = None
        if source_id != -1:
            try:
                p_data = ProjectData.objects.get(project=proj, datasource=DataSource.objects.get(pk=source_id))
            except DataSource.DoesNotExist:
                print("DataSource does not exist")
                pass
            except ProjectData.DoesNotExist:
                print("ProjectData does not exist")
                pass

            try:
                DataAccessLog.objects.get_or_create(
                    user=u, project_data=p_data, datapoint=str(dp_id),
                    is_submitted=False, is_skipped=False
                )
            except DataAccessLog.MultipleObjectsReturned:
                alogs = DataAccessLog.objects.filter(
                    user=u, project_data=p_data, datapoint=str(dp_id),
                    is_submitted=False, is_skipped=False
                ).order_by('-dt_created').all()
                for al in alogs[1:]:
                    al.delete()

            try:
                logs = DataAccessLog.objects.filter(user=u, project_data=p_data, is_submitted=True).count()
            except DataAccessLog.DoesNotExist:
                print("DataAccessLog does not exist")
                pass

        menu_items, project_markers = {}, MarkerVariant.objects.filter(project=proj)
        for m in project_markers:
            menu_items[m.marker.code] = [item.to_json() for item in MarkerContextMenuItem.objects.filter(marker=m).all()]

        ctx = {
            'text': apply_premarkers(proj, dp),
            'source_id': source_id,
            'source_size':  source_size,
            'dp_id': dp_id,
            'dp_source_name': dp_source_name,
            'source_finished': logs + 1 >= source_size if logs else False,
            'project': proj,
            'profile': u_profile
        }

        tmpl = get_template(os.path.join(proj.task_type, 'display.html'))
        data['task_type_template'] = tmpl.render(ctx, self.request)
        data['marker_actions'] = menu_items
        data['relation_repr'] = {r.pk: r.representation for r in proj.relations}

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
    ctx_cache = caches['context']

    marker_groups = json.loads(data["marker_groups"], object_pairs_hook=OrderedDict)

    is_review = data.get('is_review', 'f') == 'true'
    is_resolution = data.get('is_resolution', 'f') == 'true'

    user = request.user
    try:
        project = Project.objects.get(pk=proj)
        u_profile = UserProfile.objects.get(user=user, project=project)
        data_source = DataSource.objects.get(pk=data['datasource'])

        if not project.sampling_with_replacement:
            project_data = ProjectData.objects.get(project=project, datasource=data_source)
            dal = DataAccessLog.objects.get(user=user, project_data=project_data, datapoint=str(data['datapoint']))
            dal.is_submitted = True
            dal.save()
    except Project.DoesNotExist:
        raise Http404
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': True})
    except DataSource.DoesNotExist:
        data_source = None

    batch = Batch.objects.create(uuid=uuid.uuid4(), user=user)

    if marker_groups:
        dct = OrderedDict()
        for k, v in marker_groups.items():
            unit, i, marker, _ = k.split("_")
            prefix = "{}_{}".format(unit, i)
            if prefix not in dct:
                dct[prefix] = defaultdict(list)
            if v:
                dct[prefix][marker].append(v)
        marker_groups = dct

        if len([a for x in marker_groups.values() for y in x.values() for a in y]) > 0:
            ctx = retrieve_by_hash(data['input_context'], Context, ctx_cache)
            if not ctx:
                ctx = Context.objects.create(datasource=data_source, content=data['input_context'])
                ctx_cache.set(ctx.content_hash, ctx.pk, 3600)

            for i, (unit, v) in enumerate(marker_groups.items()):
                unit_cache = []
                for short, values in v.items():
                    marker = project.markers.filter(short=short).first()
                    mv = MarkerVariant.objects.filter(project=project, marker=marker).annotate(
                        filtered_unit=Replace('unit__name', Value('_'), Value(''))
                    ).filter(filtered_unit=unit.split("_")[0]).first()

                    N = len(values)
                    if N >= mv.min() and N <= mv.max():
                        for val in values:
                            if val:
                                unit_cache.append({
                                    'content': val,
                                    'marker': mv,
                                    'unit': i + 1
                                })
                    else:
                        unit_cache = []
                        break

                for dct in unit_cache:
                    if dct['marker'].is_free_text:
                        Input.objects.create(context=ctx, batch=batch, **dct)

    saved_labels = 0
    label_cache = {}
    for chunk in chunks:
        # inp is typically the same for all chunks
        res_chunk = process_chunk(chunk, batch, project, data_source, user, (ctx_cache, label_cache), (is_resolution, is_review))
        if res_chunk:
            ret_caches, just_saved = res_chunk
            ctx_cache, label_cache = ret_caches
            saved_labels += just_saved

    for i, rel in enumerate(relations):
        for link in rel['links']:
            source_id, target_id = int(link['s']), int(link['t'])

            try:
                source_label = Label.objects.filter(pk=label_cache.get(source_id, -1)).get()
                target_label = Label.objects.filter(pk=label_cache.get(target_id, -1)).get()
            except Label.DoesNotExist:
                continue

            try:
                rule = Relation.objects.filter(pk=rel['rule']).get()
            except Relation.DoesNotExist:
                continue

            LabelRelation.objects.create(
                rule=rule, first_label=source_label, second_label=target_label, batch=batch, unit=i+1
            )

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
        'next_task': 'regular',
        'batch': str(batch)
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

    if not project.sampling_with_replacement:
        ds_id = request.POST.get('sId')
        if ds_id:
            data_source = DataSource.objects.get(pk=ds_id)
            project_data = ProjectData.objects.get(project=project, datasource=data_source)
            dp_id = request.POST.get('dpId')
            if dp_id:
                try:
                    log = DataAccessLog.objects.get(user=request.user, project_data=project_data, datapoint=str(dp_id), is_skipped=False)
                    if not log.is_submitted:
                        log.is_skipped = True
                        log.save()
                except DataAccessLog.DoesNotExist:
                    DataAccessLog.objects.create(
                        user=request.user, project_data=project_data, datapoint=str(dp_id), 
                        is_submitted=False, is_skipped=True
                    )

    dp, dp_id, dp_source_name, source_size, source_id = project.data(request.user)

    data_source = DataSource.objects.get(pk=source_id)
    project_data, _ = ProjectData.objects.get_or_create(project=project, datasource=data_source)
    DataAccessLog.objects.create(
        user=request.user, project_data=project_data, datapoint=str(dp_id), 
        is_submitted=False, is_skipped=False
    )

    return JsonResponse({
        'text': prettify(apply_premarkers(project, dp)),
        'source_id': source_id,
        'source_size':  source_size,
        'dp_id': dp_id,
        'dp_source_name': dp_source_name
    })


@login_required
@require_http_methods("GET")
def update_participations(request):
    n = request.GET.get('n', '')
    template = ''
    if n == 'p':
        open_projects = Project.objects.filter(is_open=True).exclude(participants__in=[request.user]).all()
        template = render_to_string('partials/_open_projects.html', {}, request=request)
    elif n == 'o':
        participations = request.user.participations.all()
        template = render_to_string('partials/_participations.html', {}, request=request)
    elif n == 's':
        template = render_to_string('partials/_shared_projects.html', {}, request=request)
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
    rel_batch = LabelRelation.objects.filter(
        batch__user=user, first_label__marker__project=project).order_by('-dt_created').all()[:1].values('batch')
    last_rels = LabelRelation.objects.filter(batch__in=rel_batch).all()
    
    label_batch = Label.objects.filter(batch__user=user, marker__project=project).order_by('-dt_created').all()[:1].values('batch')
    last_labels = Label.objects.filter(batch__in=label_batch).all()
    
    last_input = ''

    if last_rels and last_labels:
        max_rel_dt_created = max(map(lambda x: x.dt_created, last_rels))
        max_lab_dt_created = max(map(lambda x: x.dt_created, last_labels))
        if max_rel_dt_created > max_lab_dt_created:
            # means relation was the latest
            for last_rel in last_rels:
                last_rel.first_label.undone = True
                last_rel.first_label.save()

                last_rel.second_label.undone = True
                last_rel.second_label.save()

                last_rel.undone = True
                last_rel.save()

            if last_rel.second_label.input:
                last_input = last_rel.second_label.input.content
        else:
            # means the label was the latest
            for last_label in last_labels:
                last_label.undone = True
                last_label.save()
            if last_label.input:
                last_input = last_label.input.content
    elif last_labels:
        for last_label in last_labels:
            last_label.undone = True
            last_label.save()
        if last_label.input:
            last_input = last_label.input.content

    return JsonResponse({
        'error': False,
        'batch': list(map(lambda x: str(x['batch']), label_batch)),
        'input': last_input,
        'submitted': u_profile.submitted() if u_profile else 'NA',
        'submitted_today': u_profile.submitted_today() if u_profile else 'NA'
    })


@login_required
@require_http_methods(["GET"])
def data_explorer(request, proj):
    def get_json_for_context(context, relations=None, labels=None):
        context_id = context.pk
        if relations is None:
            relations = LabelRelation.objects.filter(first_label__marker__project_id=proj, undone=False)
            if not is_admin:
                relations = relations.filter(batch__user=request.user)
        relations = relations.filter(Q(first_label__context_id=context_id) | Q(second_label__context_id=context_id))
        batches = relations.values_list('batch', flat=True).distinct()
        if labels is None:
            labels = Label.objects.filter(marker__project_id=proj, undone=False, context_id=context_id)
            if not is_admin:
                labels = labels.filter(batch__user=request.user)
        relation_labels = labels.filter(batch__in=batches)
        non_relation_labels = labels.exclude(batch__in=batches)
        bounded_labels = non_relation_labels.exclude(start=None)
        free_labels = non_relation_labels.filter(start=None)
        free_text_labels = Input.objects.filter(marker__project_id=proj, context_id=context_id)

        bounded = {}
        for l in bounded_labels:
            if l.batch.uuid not in bounded:
                bounded[l.batch.uuid] = {
                    'input': Input.objects.filter(batch=l.batch).first().content,
                    'labels': []
                }
            bounded[l.batch.uuid]['labels'].append(l.to_short_json())

        free_text = {}
        for inp in free_text_labels:
            uid = str(inp.batch.uuid)
            if uid not in free_text:
                free_text[uid] = {}
            if inp.unit not in free_text[uid]:
                free_text[uid][inp.unit] = []
            free_text[uid][inp.unit].append(inp.to_short_json(dt_format="%b %d %Y %H:%M:%S, %Z"))

        for key in free_text:
            free_text[key] = [sorted(it[1], key=lambda a: int(a['marker']['order'])) for it in sorted(free_text[key].items(), key=lambda x: x[0])]

        res = {
            'data': context.content,
            'bounded_labels': bounded,
            'relations': [r.to_short_json(dt_format="%b %d %Y %H:%M:%S, %Z") for r in relations
                if r.first_label.context_id == context_id or r.second_label.context_id == context_id],
            'free_labels': [l.to_short_json() for l in free_labels],
            'free_text_labels': free_text
            # 'is_static': project.context_size != 't'
        }
        return res

    project = Project.objects.filter(pk=proj).get()

    is_author, is_shared = project.author == request.user, project.shared_with(request.user)
    if is_author or is_shared or project.has_participant(request.user):
        is_admin = is_author or is_shared
        context_id = request.GET.get('context')
        if context_id:
            return JsonResponse(get_json_for_context(Context.objects.get(pk=context_id)))
    
        project_data = ProjectData.objects.filter(project=project).all()
        flagged_datapoints = DataAccessLog.objects.filter(project_data__in=project_data).exclude(flags="")
        if not is_admin:
            flagged_datapoints = flagged_datapoints.filter(user=request.user)

        relations = LabelRelation.objects.filter(first_label__marker__project=project, undone=False)
        labels = Label.objects.filter(marker__project=project, undone=False)
        if not is_admin:
            labels = labels.filter(batch__user=request.user)
            relations = relations.filter(batch__user=request.user)
        batches = relations.values_list('batch', flat=True).distinct()
        relation_labels = labels.filter(batch__in=batches)
        non_relation_labels = labels.exclude(batch__in=batches)

        inputs = Input.objects.filter(marker__project=project)

        batches = set(list(inputs.values_list('batch', flat=True).distinct())) | set(list(labels.values_list('batch', flat=True).distinct()))

        total_relations = relations.count()
        context_ids = list(inputs.exclude(context=None).values_list('context', flat=True).distinct())
        context_ids += list(labels.exclude(context=None).values_list('context', flat=True).distinct())
        if total_relations > 0:
            context_ids += list(relation_labels.exclude(context=None).values_list('context', flat=True).distinct())

        actions = defaultdict(list)
        for m in MarkerVariant.objects.filter(project=project):
            for a in m.actions.all():
                if a.admin_filter:
                    for cm_item in MarkerContextMenuItem.objects.filter(marker=m, action=a):
                        if cm_item.field:
                            actions[cm_item.verbose_admin or cm_item.verbose].append({
                                'marker': m,
                                'filter': a.admin_filter,
                                'cm': cm_item
                            })
        ctx = {
            'project': project,
            'contexts': Context.objects.filter(pk__in=context_ids),
            'total_labels': labels.count(),
            'total_relations': total_relations,
            'total_inputs': inputs.count(),
            'total_batches': len(batches),
            'flagged_datapoints': flagged_datapoints,
            'action_filters': list(actions.items())
        }
        return render(request, 'projects/data_explorer.html', ctx)
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
    exporter = globals().get('export_{}'.format(task_type), export_generic)
    if exporter:
        return JsonResponse({"data": exporter(project)})
    else:
        raise Http404


@login_required
@require_http_methods(["POST"])
def flag_text(request, proj):
    feedback = request.POST.get('feedback')
    dp_id = request.POST.get('dp_id')
    ds_id = request.POST.get('ds_id')

    project = Project.objects.filter(pk=proj).get()
    data_source = DataSource.objects.get(pk=ds_id)

    project_data = ProjectData.objects.get(project=project, datasource=data_source)
    DataAccessLog.objects.create(
        user=request.user, project_data=project_data, datapoint=str(dp_id),
        is_submitted=False, is_skipped=True, flags=feedback
    )
    return JsonResponse({})


@login_required
def time_report(request, proj):
    def calc_time(ll, dp_created):
        for b1, b2 in zip(ll[:len(ll)], ll[1:]):
            l1, l2 = b1[1][0], b2[1][0]
            try:
                if l1 and l2 and l1.dt_created and l2.dt_created and l1.dt_created.month == l2.dt_created.month and\
                    l1.dt_created.day == l2.dt_created.day and l1.dt_created.year == l2.dt_created.year:
                    timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60. / 60, 2)
                    if timing <= 2:
                        time_spent[u][f"{l1.dt_created.year}/{l1.dt_created.month}"] += timing
                    dp_created[u][f"{l1.dt_created.year}/{l1.dt_created.month}"] += len(b2[1])
            except:
                pass

    project = Project.objects.filter(pk=proj).get()

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer)

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    p.setFont("Terminator", size=18)
    system_name = "Textinator"
    p.drawString(A4[0] / 2 - 18 * PT2MM * len(system_name) * 1.1, 0.95 * A4[1], system_name)

    p.setFont("Helvetica", size=14)
    report_name = f'Time report for project "{project.title}"'
    p.drawString(A4[0] / 2 - (14 * PT2MM * len(report_name) / 2), 0.92 * A4[1], report_name)

    inputs = Input.objects.filter(marker__project__id=proj).order_by('dt_created').all()
    labels = Label.objects.filter(marker__project__id=proj, undone=False).order_by('dt_created').all()
    inputs_by_user, labels_by_user = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
    for i in inputs:
        inputs_by_user[i.batch.user.username][str(i.batch)].append(i)
    for l in labels:
        labels_by_user[l.batch.user.username][str(l.batch)].append(l)

    time_spent = defaultdict(lambda: defaultdict(int))
    inputs_created = defaultdict(lambda: defaultdict(int))
    labels_created = defaultdict(lambda: defaultdict(int))
    data = [['User', 'Month', 'Time (h)', '# of inputs', '# of labels']]
    for u in labels_by_user:
        ll = list(labels_by_user[u].items())
        calc_time(ll, labels_created)

    for u in inputs_by_user:
        ll = list(inputs_by_user[u].items())
        calc_time(ll, inputs_created)
    
    for u, td in time_spent.items():
        keys = sorted(td.keys())
        year, month = keys[0].split('/')
        data.append([u, f"{MONTH_NAMES[int(month) - 1]} {year}", round(td[keys[0]], 2), inputs_created[u][keys[0]], labels_created[u][keys[0]]])
        for k in keys[1:]:
            year, month = k.split('/')
            data.append(['', f"{MONTH_NAMES[int(month) - 1]} {year}", round(td[k], 2), inputs_created[u][k], labels_created[u][k]])

    LIST_STYLE = TableStyle([
        ('LINEABOVE', (0,0), (-1,0), 2, colors.black),
        ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 2, colors.black),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )

    t = Table(data, colWidths=[110, 110, 70, 70, 70])
    t.setStyle(LIST_STYLE)
    w, h = t.wrapOn(p, 540, 720)
    t.drawOn(p, A4[0] / 8, 0.8 * A4[1] - h)

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='time_report.pdf')
