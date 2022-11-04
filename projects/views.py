# -*- coding: utf-8 -*-
import os
import io
import time
import bisect
import uuid
import json
from collections import defaultdict

from django.http import JsonResponse, Http404, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.conf import settings
from django.template import Context
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import caches
from django.template.loader import render_to_string, get_template
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from chartjs.views.columns import BaseColumnsHighChartsView

# from modeltranslation.translator import translator

import projects.models as Tm
import projects.view_helpers as Tvh
import projects.datasources as Tds
import projects.helpers as Th
import projects.export as Tex

from Textinator.jinja2 import to_markdown, to_formatted_text
from .view_helpers import (
    BatchInfo, process_inputs, process_marker_groups, process_text_markers,
    process_chunks_and_relations, process_chunk, render_editing_board
)

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
        self.labels = Tm.Label.objects.filter(marker__project__id=self.pk, undone=False).all()
        self.inputs = Tm.Input.objects.filter(marker__project__id=self.pk).all()
        self.x_axis = sorted(set([len(l.text.split()) for l in self.labels]) | set([len(i.content.split()) for i in self.inputs]))
        self.project = Tm.Project.objects.get(pk=self.pk)
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
                if hasattr(l, 'text'):
                    data[self.p2i[l.marker.marker.name]][self.l2i[len(l.text.split())]] += 1
                elif hasattr(l, 'content'):
                    data[self.p2i[l.marker.marker.name]][self.l2i[len(l.content.split())]] += 1
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
        inputs = Tm.Input.objects.filter(marker__project__id=self.pk).order_by('dt_created').all()
        labels = Tm.Label.objects.filter(marker__project__id=self.pk, undone=False).order_by('dt_created').all()
        self.inputs_by_user = defaultdict(lambda: defaultdict(list))
        self.labels_by_user = defaultdict(lambda: defaultdict(list))
        for inp in inputs:
            self.inputs_by_user[inp.batch.user.username][str(inp.batch)].append(inp)
        for lab in labels:
            self.labels_by_user[lab.batch.user.username][str(lab.batch)].append(lab)

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

            self.project = Tm.Project.objects.get(pk=self.pk)
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
                        l1, l2 = b1[1][0], b2[1][0]
                        if l1 and l2 and l1.dt_created and l2.dt_created:
                            timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1)
                            if timing > 0 and timing < 120:
                                pos = bisect.bisect(self.x_axis, timing)
                                data[self.p2i[u]][pos - 1] += 1
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
        logs = Tm.DataAccessLog.objects.filter(project__id=self.pk)
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

        self.project = Tm.Project.objects.get(pk=self.pk)
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
        self.project = Tm.Project.objects.get(pk=self.pk)
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
    model = Tm.Project
    template_name = 'projects/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['languages'] = settings.LANGUAGES
        return context


class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Tm.Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    permission_denied_message = 'you did not confirmed yet. please check your email.'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        con = DetailView.context_object_name
        proj = data[con]

        u = self.request.user
        if not proj.has_participant(u): raise Http404

        fallback_languages = (proj.language, u.profile.preferred_language, 'en')
        Tm.Marker.name.fallback_languages = {'default': fallback_languages}
        Tm.Relation.name.fallback_languages = {'default': fallback_languages}

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

        u_profile = Tm.UserProfile.objects.filter(user=u, project=proj).get()

        dp_info = proj.data(u)

        logs = None
        if dp_info.source_id:
            try:
                d = Tm.DataSource.objects.get(pk=dp_info.source_id)
            except Tm.DataSource.DoesNotExist:
                print("DataSource does not exist")
                raise Http404

            if dp_info.is_delayed:
                dal = Tm.DataAccessLog.objects.filter(
                    user=u, datapoint=str(dp_info.id),
                    project=proj, datasource=d,
                    is_submitted=False, is_skipped=False,
                    is_delayed=True
                ).order_by('-dt_updated').first()
                dal.is_delayed = False
                dal.save()
            else:
                if proj.is_sampled(replacement=True):
                    dal = Tm.DataAccessLog.objects.create(
                        user=u, datapoint=str(dp_info.id),
                        project=proj, datasource=d,
                        is_submitted=False
                    )
                else:
                    if proj.auto_text_switch:
                        Tm.DataAccessLog.objects.get_or_create(
                            user=u, project=proj, datasource=d, datapoint=str(dp_info.id),
                            is_submitted=False
                        )
                    else:
                        Tm.DataAccessLog.objects.get_or_create(
                            user=u, project=proj, datasource=d, datapoint=str(dp_info.id),
                            is_skipped=False
                        )

                try:
                    logs = Tm.DataAccessLog.objects.filter(user=u, project=proj, datasource=d, is_submitted=True).count()
                except Tm.DataAccessLog.DoesNotExist:
                    print("DataAccessLog does not exist")
                    pass

        menu_items, project_markers = {}, Tm.MarkerVariant.objects.filter(project=proj)
        for m in project_markers:
            menu_items[m.marker.code] = [item.to_json() for item in Tm.MarkerContextMenuItem.objects.filter(marker=m).all()]

        if dp_info.is_empty:
            text = render_to_string('partials/_great_job.html')
        else:
            if type(dp_info.text) == Tds.TextDatapoint:
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
                text = Th.apply_premarkers(proj, text).strip()

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
        dal = Tm.DataAccessLog.objects.filter(
            user=batch_info.user,
            datapoint=batch_info.datapoint,
            project=batch_info.project,
            datasource=batch_info.data_source
        ).order_by('-dt_updated').first()
        dal.is_submitted = True
        dal.is_delayed = False
        dal.save()

        batch = Tm.Batch.objects.create(uuid=uuid.uuid4(), user=batch_info.user)

        process_inputs(batch, batch_info, ctx_cache=ctx_cache)
        process_marker_groups(batch, batch_info, ctx_cache=ctx_cache)
        process_text_markers(batch, batch_info, ctx_cache=ctx_cache) # markers for the whole text
        process_chunks_and_relations(batch, batch_info, ctx_cache=ctx_cache)
    elif mode == 'e':
        # editing
        batch_uuid = data.get('batch')
        try:
            batch = Tm.Batch.objects.get(uuid=batch_uuid, user=batch_info.user)
        except Batch.MultipleObjectsReturned:
            return JsonResponse({'error': True})

        if batch:
            batch_inputs = {i.hash: i for i in Tm.Input.objects.filter(batch=batch)}
            batch_labels = {l.hash: l for l in Tm.Label.objects.filter(batch=batch)}

            inputs = []
            for input_type, changed_inputs in batch_info.inputs():
                for name, changed in changed_inputs.items():
                    if isinstance(changed, dict):
                        try:
                            inp = batch_inputs[changed['hash']]
                            if inp.marker.code == name:
                                inp.content = changed['value']
                                inputs.append(inp)
                        except KeyError:
                            # smth is wrong
                            pass
                    elif isinstance(changed, str):
                        # we create a new record!
                        try:
                            data_source = Tm.DataSource.objects.get(pk=data['datasource'])
                        except Tm.DataSource.DoesNotExist:
                            data_source = None

                        if data_source:
                            kwargs = {
                                input_type: {
                                    name: changed
                                }
                            }
                            process_inputs(batch, batch_info, **kwargs)

            if inputs:
                Tm.Input.objects.bulk_update(inputs, ['content'])

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
        'mode': mode,
        'trigger_update': batch_info.project.auto_text_switch
    })


@login_required
@require_http_methods(["GET"])
def editing(request, proj):
    page = int(request.GET.get("p", 1))
    project = get_object_or_404(Tm.Project, pk=proj)
    return JsonResponse({
        'template': render_editing_board(project, request.user, page)
    })


@login_required
@require_http_methods(["GET"])
def get_batch(request):
    # TODO: ensure that the request cannot be triggered by external tools
    uuid = request.GET.get('uuid', '')
    if uuid:
        labels = Tm.Label.objects.filter(batch__uuid=uuid)
        inputs = Tm.Input.objects.filter(batch__uuid=uuid)

        context = None
        if labels.count():
            context = labels.first().context.to_json()
        elif inputs.count():
            context = inputs.first().context.to_json()

        non_unit_markers_q = inputs.filter(marker__unit=None)
        non_unit_markers = {}
        input_types = ['free-text', 'lfree-text', 'integer', 'float', 'range', 'radio', 'check']
        for it in input_types:
            non_unit_markers[it.replace('-', '_')] = non_unit_markers_q.filter(marker__anno_type=it)
        groups = inputs.exclude(marker__unit=None)

        span_labels = labels.filter(marker__anno_type='m-span')
        text_labels = labels.filter(marker__anno_type='m-text')

        # context['content'] will give us text without formatting,
        # so we simply query the data source one more time to get with formatting
        ds = Tm.DataSource.objects.get(pk=context['ds_id'])
        context['content'] = to_markdown(ds.postprocess(ds.get(context['dp_id'])).strip())

        return JsonResponse({
            'context': context,
            'span_labels': [s_label.to_short_json() for s_label in span_labels],
            'text_labels': [t_label.to_short_json() for t_label in text_labels],
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
            c = Tm.Context.objects.get(pk=cpk)
            return JsonResponse({
                "context": c.content
            })
        except Tm.Context.DoesNotExist:
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
            inputs = Tm.Input.objects.filter(
                context_id=cpk,
                marker__project_id=proj,
                batch__user_id=upk
            ).order_by('batch_id')
            labels = Tm.Label.objects.filter(
                context_id=cpk,
                marker__project_id=proj,
                batch__user_id=upk
            ).order_by('batch_id')

            annotations = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

            Ni, Nl = len(inputs), len(labels)

            if Nl == 0 and Ni == 0:
                return JsonResponse({})
            elif Nl == 0:
                for inp in inputs:
                    annotations[str(inp.batch)][inp.group_order]['inputs'].append(inp.to_minimal_json(include_color=True))
                    annotations[str(inp.batch)]['created'] = inp.batch.dt_created.strftime("%-d %B %Y, %H:%M:%S")

                    if request.user.is_superuser:
                        annotations[str(inp.batch)]['id'] = inp.batch_id
            elif Ni == 0:
                for lab in labels:
                    annotations[str(lab.batch)][lab.group_order]['labels'].append(lab.to_minimal_json(include_color=True))
                    annotations[str(lab.batch)]['created'] = lab.batch.dt_created.strftime("%-d %B %Y, %H:%M:%S")

                    if request.user.is_superuser:
                        annotations[str(lab.batch)]['id'] = lab.batch_id
            else:
                # linear scan
                i_id, l_id = 0, 0
                i_changed, l_changed = True, True
                while i_id < Ni and l_id < Nl:
                    i_batch_id = inputs[i_id].batch_id
                    l_batch_id = labels[l_id].batch_id

                    if i_changed:
                        annotations[str(inputs[i_id].batch)][inputs[i_id].group_order]['inputs'].append(
                            inputs[i_id].to_minimal_json(include_color=True)
                        )
                        annotations[str(inputs[i_id].batch)]['created'] = inputs[i_id].batch.dt_created.strftime("%-d %B %Y, %H:%M:%S")
                        if request.user.is_superuser:
                            annotations[str(inputs[i_id].batch)]['id'] = inputs[i_id].batch_id
                        i_changed = False
                    if l_changed:
                        annotations[str(labels[l_id].batch)][labels[l_id].group_order]['labels'].append(
                            labels[l_id].to_minimal_json(include_color=True)
                        )
                        annotations[str(labels[l_id].batch)]['created'] = labels[l_id].batch.dt_created.strftime("%-d %B %Y, %H:%M:%S")
                        if request.user.is_superuser:
                            annotations[str(labels[l_id].batch)]['id'] = labels[l_id].batch_id
                        l_changed = False

                    if i_batch_id < l_batch_id:
                        i_id += 1
                        i_changed = True
                    elif i_batch_id > l_batch_id:
                        l_id += 1
                        l_changed = True
                    else:
                        i_id += 1
                        l_id += 1
                        i_changed, l_changed = True, True

            return JsonResponse({
                "annotations": annotations
            })
        except Tm.Context.DoesNotExist:
            return JsonResponse({
                "error": "No such text"
            })
    else:
        return JsonResponse({})


@login_required
@require_http_methods(["GET", "POST"])
def join_or_leave_project(request, proj):
    project = get_object_or_404(Tm.Project, pk=proj)
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
    profiles = Tm.UserProfile.objects.filter(user=user).all()
    return render(request, 'projects/profile.html', {
        'total_participated': len(profiles),
        'total_points': sum(map(lambda x: x.points, profiles)),
        'user': user
    })


# TODO: fix error that sometimes happens -- PayloadTooLargeError: request entity too large
@login_required
@require_http_methods("POST")
def new_article(request, proj):
    project = Tm.Project.objects.get(pk=proj)

    # log the old one
    ds_id = request.POST.get('sId')
    if ds_id:
        data_source = Tm.DataSource.objects.get(pk=ds_id)
        dp_id = request.POST.get('dpId')
        save_for_later = request.POST.get('saveForLater') == "true"
        if dp_id:
            try:
                log = Tm.DataAccessLog.objects.get(
                    user=request.user, project=project,
                    datasource=data_source, datapoint=str(dp_id), is_skipped=False
                )
                log.is_skipped = not save_for_later
                log.is_delayed = save_for_later
                log.save()
            except Tm.DataAccessLog.DoesNotExist:
                Tm.DataAccessLog.objects.create(
                    user=request.user, project=project,
                    datasource=data_source, datapoint=str(dp_id),
                    is_submitted=False, is_skipped=not save_for_later,
                    is_delayed=save_for_later
                )

    dp_info = project.data(request.user, True)
    request.session['dp_info_{}'.format(proj)] = dp_info.to_json()

    if dp_info.is_empty:
        text = render_to_string('partials/_great_job.html')
    else:
        data_source = Tm.DataSource.objects.get(pk=dp_info.source_id)
        if dp_info.is_delayed:
            log = Tm.DataAccessLog.objects.get(
                user=request.user, datapoint=str(dp_info.id),
                project=project, datasource=data_source,
                is_submitted=False, is_skipped=False,
                is_delayed=True
            )
            log.is_delayed = False
            log.save()
        else:
            Tm.DataAccessLog.objects.get_or_create(
                user=request.user, datapoint=str(dp_info.id),
                project=project, datasource=data_source,
                is_submitted=False, is_skipped=False,
                is_delayed=False
            )

        text = Th.apply_premarkers(project, dp_info.text)

        if dp_info.source_formatting == 'md':
            text = to_markdown(text)
        elif dp_info.source_formatting == 'ft':
            text = to_formatted_text(text)

    return JsonResponse({
        'text': text,
        'dp_info': dp_info.to_json()
    })


@login_required
@require_http_methods("POST")
def undo_last(request, proj):
    user = request.user
    project = Tm.Project.objects.get(pk=proj)

    try:
        u_profile = Tm.UserProfile.objects.get(user=user, project=project)
    except Tm.UserProfile.DoesNotExist:
        u_profile = None

    # find a last relation submitted if any
    rel_batch = Tm.LabelRelation.objects.filter(
        batch__user=user, first_label__marker__project=project).order_by('-dt_created').all()[:1].values('batch')
    last_rels = Tm.LabelRelation.objects.filter(batch__in=rel_batch).all()

    label_batch = Tm.Label.objects.filter(batch__user=user, marker__project=project).order_by('-dt_created').all()[:1].values('batch')
    last_labels = Tm.Label.objects.filter(batch__in=label_batch).all()

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
    project = Tm.Project.objects.filter(pk=proj).get()

    is_author, is_shared = project.author == request.user, project.shared_with(request.user)
    if is_author or is_shared or project.has_participant(request.user):
        is_admin = is_author or is_shared

        flagged_datapoints = Tm.DataAccessLog.objects.filter(project=project).exclude(flags="").order_by('-dt_updated')
        if not is_admin:
            flagged_datapoints = flagged_datapoints.filter(user=request.user)

        relations = Tm.LabelRelation.objects.filter(first_label__marker__project=project, undone=False)
        labels = Tm.Label.objects.filter(marker__project=project, undone=False)
        if not is_admin:
            labels = labels.filter(batch__user=request.user)
            relations = relations.filter(batch__user=request.user)

        inputs = Tm.Input.objects.filter(marker__project=project)
        batch_ids = set(list(inputs.values_list('batch', flat=True).distinct())) | set(list(labels.values_list('batch', flat=True).distinct()))
        total_relations = relations.count()

        context_ids = set(list(inputs.values_list('context_id', flat=True).distinct())) | set(list(labels.values_list('context_id', flat=True).distinct()))
        contexts = Tm.Context.objects.filter(id__in=context_ids).all()

        ctx = {
            'project': project,
            'total_labels': labels.count(),
            'total_relations': total_relations,
            'total_inputs': inputs.count(),
            'total_batches': len(batch_ids),
            'flagged_datapoints': flagged_datapoints[:300],
            'flagged_num': flagged_datapoints.count(),
            'contexts': contexts
        }
        return render(request, 'projects/data_explorer.html', ctx)
    else:
        raise Http404


@login_required
@require_http_methods(["GET"])
def get_data(request, source_id, dp_id):
    try:
        ds = Tm.DataSource.objects.get(pk=source_id)
        return render(request, 'projects/raw_datapoint.html', {
            'ds': ds,
            'text': ds.get(dp_id)
        })
    except Tm.DataSource.DoesNotExist:
        raise Http404


@login_required
@require_http_methods(["POST"])
def async_delete_input(request, proj, inp):
    try:
        Tm.Input.objects.filter(pk=inp).delete()
    except:
        pass
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
@require_http_methods(["GET"])
def export(request, proj):
    try:
        project = Tm.Project.objects.get(pk=proj)
        exporter = Tex.Exporter(project, config={
            'consolidate_clusters': request.GET.get('consolidate_clusters') == 'on',
            'include_usernames': request.GET.get('include_usernames', False)
        })
        return JsonResponse({"data": exporter.export()})
    except Tm.Project.DoesNotExist:
        raise Http404


@login_required
@require_http_methods(["POST"])
def flag_text(request, proj):
    feedback = json.loads(request.POST.get('feedback'))
    dp_id = request.POST.get('dp_id')
    ds_id = request.POST.get('ds_id')

    project = Tm.Project.objects.filter(pk=proj).get()
    data_source = Tm.DataSource.objects.get(pk=ds_id)

    dal, _ = Tm.DataAccessLog.objects.get_or_create(
        user=request.user, datapoint=str(dp_id),
        project=project, datasource=data_source,
        is_submitted=False
    )
    if not dal.flags:
        dal.flags = {}
    flags = dal.flags
    if 'text_errors' not in flags:
        flags['text_errors'] = {}
    ts = time.time()
    flags['text_errors'][ts] = feedback
    dal.flags = flags
    dal.save()
    return JsonResponse({})


@login_required
@require_http_methods(["POST"])
def flagged_search(request, proj):
    project = Tm.Project.objects.get(pk=proj)
    data = json.loads(request.body)
    query = data.get('query')

    is_author, is_shared = project.author == request.user, project.shared_with(request.user)

    if is_author or is_shared or project.has_participant(request.user):
        is_admin = is_author or is_shared

        flagged = Tm.DataAccessLog.objects.filter(project=project).exclude(
            flags="")
        if not is_admin:
            flagged = flagged.filter(user=request.user)

    if query:
        vector = SearchVector('flags')
        query = SearchQuery(query)
        res = flagged.annotate(
            search=vector
        ).filter(
            search=query
        ).annotate(
            rank=SearchRank(vector, query)
        ).order_by('-rank')
    else:
        res = flagged.order_by('-dt_created')
    return JsonResponse({
        "res": render_to_string('partials/_flagged_summary.html', {
            'flagged_datapoints': res
        })
    })


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

    project = Tm.Project.objects.filter(pk=proj).get()

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

    inputs = Tm.Input.objects.filter(marker__project__id=proj).order_by('dt_created').all()
    labels = Tm.Label.objects.filter(marker__project__id=proj, undone=False).order_by('dt_created').all()
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
