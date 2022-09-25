import json
import os
import io
import random
import bisect
import uuid
from collections import defaultdict
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
from django.db.models import Q
from django.urls import reverse

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from chartjs.views.columns import BaseColumnsHighChartsView
from chartjs.views.lines import BaseLineChartView

from modeltranslation.translator import translator

from .models import *
from .helpers import hash_text, retrieve_by_hash, apply_premarkers
from .export import Exporter
from .view_helpers import *
from .datasources import TextDatapoint

from Textinator.jinja2 import to_markdown, to_formatted_text


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
        logs = DataAccessLog.objects.filter(project__id=self.pk)
        submitted_logs = logs.filter(is_submitted=True)
        skipped_logs = logs.filter(is_skipped=True, is_submitted=False)
        
        self.submitted_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.skipped_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.dataset_info = {}
        self.l2i, i = {}, 0
        for logs_data, logs_storage in zip(
            [submitted_logs, skipped_logs], 
            [self.submitted_logs_by_ds_and_user, self.skipped_logs_by_ds_and_user]):
            for l in logs_data:
                ds = l.datasource
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['languages'] = settings.LANGUAGES
        return context


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

        dp_info = proj.data(u)

        logs = None
        if dp_info.source_id:
            try:
                d = DataSource.objects.get(pk=dp_info.source_id)
            except DataSource.DoesNotExist:
                print("DataSource does not exist")
                pass

            if proj.is_sampled(replacement=True):
                try:
                    dal = DataAccessLog.objects.get(
                        user=u, datapoint=str(dp_info.id), 
                        project=proj, datasource=d
                    )
                except DataAccessLog.DoesNotExist:
                    dal = DataAccessLog.objects.create(
                        user=u, datapoint=str(dp_info.id), 
                        project=proj, datasource=d,
                        is_submitted=False, is_skipped=False
                    )
            else:
                if proj.auto_text_switch:
                    DataAccessLog.objects.get_or_create(
                        user=u, project=proj, datasource=d, datapoint=str(dp_info.id),
                        is_submitted=False, is_skipped=False
                    )
                else:
                    DataAccessLog.objects.get_or_create(
                        user=u, project=proj, datasource=d, datapoint=str(dp_info.id),
                        is_skipped=False
                    )

            try:
                logs = DataAccessLog.objects.filter(user=u, project=proj, datasource=d, is_submitted=True).count()
            except DataAccessLog.DoesNotExist:
                print("DataAccessLog does not exist")
                pass

        menu_items, project_markers = {}, MarkerVariant.objects.filter(project=proj)
        for m in project_markers:
            menu_items[m.marker.code] = [item.to_json() for item in MarkerContextMenuItem.objects.filter(marker=m).all()]

        if dp_info.is_empty:
            text = render_to_string('partials/_great_job.html')
        else:
            if type(dp_info.text) == TextDatapoint:
                users = list(set([x['username'] for x in dp_info.text.meta if 'username' in x]))
                text = render_to_string('partials/components/areas/dialogue_text.html', {
                    'dp_info': dp_info,
                    'cmap': {
                        users[0]: 'info',
                        users[1]: 'primary'
                    }
                })
                dp_info.is_dialogue = True
            else:
                text = dp_info.text

            if not dp_info.no_data:
                text = apply_premarkers(proj, text).strip()

        ctx = {
            'text': text,
            'dp_info': dp_info,
            'source_finished': (logs + 1) >= dp_info.source_size if logs else False,
            'project': proj,
            'profile': u_profile
        }

        self.request.session['dp_info_{}'.format(proj.pk)] = dp_info.to_json()

        tmpl = get_template(os.path.join('projects', 'task_types', '{}.html'.format(proj.task_type)))
        data['task_type_template'] = tmpl.render(ctx, self.request)
        data['marker_actions'] = menu_items
        data['relation_repr'] = {r.pk: r.representation for r in proj.relationvariant_set.all()}

        return data

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)
        except Http404:
            if hasattr(self, 'object'):
                return redirect('projects:join_or_leave', proj=self.object.pk)
            else:
                raise Http404


@login_required
@require_http_methods(["POST"])
def record_datapoint(request, proj):
    data = request.POST
    ctx_cache = caches['context']
    mode = data['mode']

    batch_info = BatchInfo(data, proj, request.user)

    if mode == 'r':
        # # regular submission
        if not batch_info.project or not batch_info.data_source:
            raise Http404

        # log the submission
        dal = DataAccessLog.objects.get(
            user=batch_info.user,
            datapoint=batch_info.datapoint,
            project=batch_info.project,
            datasource=batch_info.data_source
        )
        dal.is_submitted = True
        dal.save()

        batch = Batch.objects.create(uuid=uuid.uuid4(), user=batch_info.user)

        process_inputs(batch, batch_info, ctx_cache=ctx_cache)
        process_marker_groups(batch, batch_info, ctx_cache=ctx_cache)
        process_text_markers(batch, batch_info, ctx_cache=ctx_cache) # markers for the whole text
        process_chunks_and_relations(batch, batch_info, ctx_cache=ctx_cache)
    elif mode == 'e':
        # editing
        batch_uuid = data.get('batch')
        try:
            batch = Batch.objects.get(uuid=batch_uuid, user=batch_info.user)
        except Batch.MultipleObjectsReturned:
            return JsonResponse({'error': True})
        
        if batch:
            batch_inputs = {i.hash: i for i in Input.objects.filter(batch=batch)}
            batch_labels = {l.hash: l for l in Label.objects.filter(batch=batch)}

            inputs = []
            for input_type, changed_inputs in batch_info.inputs():
                for name, changed in changed_inputs.items():
                    if type(changed) == dict:
                        try:
                            inp = batch_inputs[changed['hash']]
                            if inp.marker.code == name:
                                inp.content = changed['value']
                                inputs.append(inp)
                        except KeyError:
                            # smth is wrong
                            pass
                    elif type(changed) == str:
                        # we create a new record!
                        try:
                            data_source = DataSource.objects.get(pk=data['datasource'])
                        except DataSource.DoesNotExist:
                            data_source = None
                        
                        if data_source:
                            kwargs = {
                                input_type: {
                                    name: changed
                                }
                            }
                            process_inputs(batch, batch_info, **kwargs)

            if inputs:
                Input.objects.bulk_update(inputs, ['content'])

            for chunk in batch_info.chunks:
                if chunk.get('deleted', False):
                    chunk_hash = chunk.get('hash')
                    if chunk_hash and chunk_hash in batch_labels:
                        batch_labels[chunk_hash].delete()
            process_chunks_and_relations(batch, batch_info)

            batch.save() # this updates dt_updated
            
            return JsonResponse({
                'error': False,
                'mode': mode,
                'template': render_editing_board(batch_info.project, batch_info.user)
            })
        else:
            return JsonResponse({'error': True})
        

    return JsonResponse({
        'error': False,
        'batch': str(batch),
        'mode': mode
    })


@login_required
@require_http_methods(["GET"])
def editing(request, proj):
    project = get_object_or_404(Project, pk=proj)
    return JsonResponse({
        'template': render_editing_board(project, request.user)
    })


@login_required
@require_http_methods(["GET"])
def get_batch(request):
    # TODO: ensure that the request cannot be triggered by external tools
    uuid = request.GET.get('uuid', '')
    if uuid:
        labels = Label.objects.filter(batch__uuid=uuid)
        inputs = Input.objects.filter(batch__uuid=uuid)

        context = None
        if labels.count():
            context = labels.first().context.to_json()
        elif inputs.count():
            context = inputs.first().context.to_json()

        non_unit_markers_q = inputs.filter(marker__unit=None)
        non_unit_markers = {}
        input_types = ['free-text', 'lfree-text', 'integer', 'float', 'range']
        for it in input_types:
            non_unit_markers[it.replace('-', '_')] = non_unit_markers_q.filter(marker__anno_type=it)
        groups = inputs.exclude(marker__unit=None)

        span_labels = labels.filter(marker__anno_type='m-span')
        text_labels = labels.filter(marker__anno_type='m-text')

        # context['content'] will give us text without formatting,
        # so we simply query the data source one more time to get with formatting
        ds = DataSource.objects.get(pk=context['ds_id'])
        context['content'] = to_markdown(ds.postprocess(ds.get(context['dp_id'])).strip())

        return JsonResponse({
            'context': context,
            'span_labels': [l.to_short_json() for l in span_labels],
            'text_labels': [l.to_short_json() for l in text_labels],
            'non_unit_markers': {k: [i.to_short_json() for i in v] for k, v in non_unit_markers.items()},
            'groups': [i.to_short_json() for i in groups]
        })
    else:
        return JsonResponse({})

@login_required
@require_http_methods(["GET"])
def get_context(request, proj):
    cpk = request.GET.get('c', '')

    if cpk:
        try:
            c = Context.objects.get(pk=cpk)
            return JsonResponse({
                "context": c.content
            })
        except Context.DoesNotExist:
            return JsonResponse({
                "error": "does_not_exist"
            })
    else:
        return JsonResponse({
            "error": "does_not_exist"
        })

@login_required
@require_http_methods(["GET"])
def get_annotations(request, proj):
    cpk = request.GET.get('c', '')
    upk = request.GET.get('u', '')

    if cpk and upk:
        try:
            inputs = Input.objects.filter(
                context_id=cpk,
                marker__project_id=proj,
                batch__user_id=upk
            ).order_by('batch_id')
            labels = Label.objects.filter(
                context_id=cpk,
                marker__project_id=proj,
                batch__user_id=upk
            ).order_by('batch_id')

            annotations = defaultdict(lambda: defaultdict(list))

            # linear scan
            i, l = 0, 0
            i_changed, l_changed = True, True
            Ni, Nl = len(inputs), len(labels)
            while i < Ni and l < Nl:
                i_batch_id = inputs[i].batch_id
                l_batch_id = labels[l].batch_id
                
                if i_changed:
                    annotations[str(inputs[i].batch)]['inputs'].append(
                        inputs[i].to_minimal_json(include_color=True)
                    )
                    annotations[str(inputs[i].batch)]['created'] = inputs[i].batch.dt_created.strftime("%-d %B %Y, %H:%M:%S")
                    i_changed = False
                if l_changed:
                    annotations[str(labels[l].batch)]['labels'].append(
                        labels[l].to_minimal_json(include_color=True)
                    )
                    l_changed = False

                if i_batch_id < l_batch_id:
                    i += 1
                    i_changed = True
                elif i_batch_id > l_batch_id:
                    l += 1
                    l_changed = True
                else:
                    i += 1
                    l += 1
                    i_changed, l_changed = True, True

            return JsonResponse({
                "annotations": annotations
            })
        except Context.DoesNotExist:
            return JsonResponse({
                "error": "No such text"
            }) 
    else:
        return JsonResponse({})


@login_required
@require_http_methods(["GET", "POST"])
def join_or_leave_project(request, proj):
    project = get_object_or_404(Project, pk=proj)
    current_user = request.user
    if request.method == "POST":
        res = {
            'error': False,
            'result': '',
            'template': ''
        }
        if project.participants.filter(pk=current_user.pk).exists():
            project.participants.remove(current_user)
            res['result'] = 'left'
        else:
            project.participants.add(current_user)
            res['result'] = 'joined'
            res['template'] = render_to_string('partials/_view_button.html', {'project': project}, request=request)
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

    # log the old one
    ds_id = request.POST.get('sId')
    if ds_id:
        data_source = DataSource.objects.get(pk=ds_id)
        dp_id = request.POST.get('dpId')
        if dp_id:
            try:
                log = DataAccessLog.objects.get(
                    user=request.user, project=project,
                    datasource=data_source, datapoint=str(dp_id), is_skipped=False
                )
                log.is_skipped = True
                log.save()
            except DataAccessLog.DoesNotExist:
                DataAccessLog.objects.create(
                    user=request.user, project=project,
                    datasource=data_source, datapoint=str(dp_id), 
                    is_submitted=False, is_skipped=True
                )

    dp_info = project.data(request.user, True)
    request.session['dp_info_{}'.format(proj)] = dp_info.to_json()

    if dp_info.is_empty:
        text = render_to_string('partials/_great_job.html')
    else:
        data_source = DataSource.objects.get(pk=dp_info.source_id)
        if project.is_sampled(replacement=True) or project.is_ordered():
            DataAccessLog.objects.get_or_create(
                user=request.user, datapoint=str(dp_info.id), 
                project=project, datasource=data_source,
                is_submitted=False, is_skipped=False
            )
        else:
            # log the new one
            DataAccessLog.objects.create(
                user=request.user, datapoint=str(dp_info.id), 
                project=project, datasource=data_source,
                is_submitted=False, is_skipped=False
            )

        text = apply_premarkers(project, dp_info.text)

        if dp_info.source_formatting == 'md':
            text = to_markdown(text)
        elif dp_info.source_formatting == 'ft':
            text = to_formatted_text(text)

    return JsonResponse({
        'text': text,
        'dp_info': dp_info.to_json()
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
    project = Project.objects.filter(pk=proj).get()

    is_author, is_shared = project.author == request.user, project.shared_with(request.user)
    if is_author or is_shared or project.has_participant(request.user):
        is_admin = is_author or is_shared
    
        flagged_datapoints = DataAccessLog.objects.filter(project=project).exclude(flags="")
        if not is_admin:
            flagged_datapoints = flagged_datapoints.filter(user=request.user)

        relations = LabelRelation.objects.filter(first_label__marker__project=project, undone=False)
        labels = Label.objects.filter(marker__project=project, undone=False)
        if not is_admin:
            labels = labels.filter(batch__user=request.user)
            relations = relations.filter(batch__user=request.user)

        inputs = Input.objects.filter(marker__project=project)
        batch_ids = set(list(inputs.values_list('batch', flat=True).distinct())) | set(list(labels.values_list('batch', flat=True).distinct()))
        total_relations = relations.count()

        context_ids = set(list(inputs.values_list('context_id', flat=True).distinct())) | set(list(labels.values_list('context_id', flat=True).distinct()))
        contexts = Context.objects.filter(id__in=context_ids).all()

        ctx = {
            'project': project,
            'total_labels': labels.count(),
            'total_relations': total_relations,
            'total_inputs': inputs.count(),
            'total_batches': len(batch_ids),
            'flagged_datapoints': flagged_datapoints,
            'contexts': contexts
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
    try:
        project = Project.objects.get(pk=proj)
        exporter = Exporter(project, config={
            'consolidate_clusters': request.GET.get('consolidate_clusters') == 'on',
            'include_usernames': request.GET.get('include_usernames', False)
        })
        return JsonResponse({"data": exporter.export()})
    except Project.DoesNotExist:
        raise Http404

@login_required
@require_http_methods(["POST"])
def flag_text(request, proj):
    feedback = request.POST.get('feedback')
    dp_id = request.POST.get('dp_id')
    ds_id = request.POST.get('ds_id')

    project = Project.objects.filter(pk=proj).get()
    data_source = DataSource.objects.get(pk=ds_id)

    DataAccessLog.objects.create(
        user=request.user, datapoint=str(dp_id),
        project=project, datasource=data_source,
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
    p.setFont("ROBOTECH GP", size=36)
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


@login_required
@require_http_methods(["GET"])
def project_meta(request, proj):
    referer = request.META.get("HTTP_REFERER")
    expected_referer = reverse('projects:detail', kwargs={'pk': proj})

    if referer and referer.endswith(expected_referer):
        json_dp_info = request.session['dp_info_{}'.format(proj)]
        return render(request, 'projects/meta.html', {
            'meta': json_dp_info['meta']
        })
    else:
        raise Http404
