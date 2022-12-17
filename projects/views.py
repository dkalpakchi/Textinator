# -*- coding: utf-8 -*-
import os
import io
import time
import uuid
import json
import logging
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
from django.contrib.postgres.fields.jsonb import KeyTransform
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

from celery.result import AsyncResult

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
from .tasks import get_label_lengths_stats, get_user_timings_stats, get_user_progress_stats, get_data_source_sizes_stats

PT2MM = 0.3527777778
MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December']

logger = logging.getLogger(__name__)

##
## Chart views
##

@login_required
@require_http_methods(["GET"])
def chart_start(request, pk):
    task = request.GET.get("task")
    token = None
    if task:
        ctask, is_created = Tm.CeleryTask.objects.get_or_create(
                task=task, project_id=pk, finished=False
        )
        if is_created:
            task_func = globals().get('get_{}_stats'.format(task))
            if task_func:
                r = task_func.delay(pk)
                token = r.task_id
                ctask.token = token
                ctask.save()
        else:
            token = ctask.token

    if token is None:
        return JsonResponse({ "token": False })
    else:
        return JsonResponse({ 'token': token })


@login_required
@require_http_methods(["GET"])
def chart_status(request, pk):
    task_id = request.GET.get("token")
    response = {
        'ready': False
    }
    if task_id:
        res = AsyncResult(task_id)
        if res.ready():
            response['ready'] = True
            if res.successful():
                response['data'] = res.get()
                response['error'] = False
            else:
                response['error'] = True
                logger.error(res.traceback)
            try:
                ctask = Tm.CeleryTask.objects.get(
                        token=task_id, project_id=pk, finished=False
                )
                ctask.finished = True
                ctask.save()
            except Tm.CeleryTask.DoesNotExist:
                logger.error("Celery task with token {} does not exist".format(task_id))

    return JsonResponse(response)


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

    batch_info = BatchInfo(data, proj, request.user, mode)

    if mode == 'r':
        # regular submission
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
    elif mode == 'e' or mode == "rev":
        # editing (e) or reviewing (rev)
        batch_uuid = data.get('batch')
        is_project_author = batch_info.project.author == batch_info.user
        is_project_shared = batch_info.project.shared_with(batch_info.user)

        try:
            page = int(data.get('p', 1))
            scope = int(data.get("scope", -1))
        except ValueError:
            page, scope = 1, -1
        query = data.get("query", "")

        if scope < 0:
            scope = None

        original_mode = mode
        if batch_info.project.editing_as_revision and mode == 'e':
            mode = 'rev'

        if mode == "e":
            if is_project_author or is_project_shared:
                batches = Tm.Batch.objects.filter(uuid=batch_uuid).all()
            else:
                batches = Tm.Batch.objects.filter(uuid=batch_uuid, user=batch_info.user).all()
        elif mode == "rev":
            profile = Tm.UserProfile.objects.get(
                user=batch_info.user, project=batch_info.project
            )

            is_admin = is_project_author or is_project_shared

            is_reviewer = profile.allowed_reviewing

            if is_admin or is_reviewer:
                # not necessarily one's own batches, but require a reviewer permission
                batches = Tm.Batch.objects.filter(uuid=batch_uuid).all()
            else:
                batches = []

        batch = None
        for b in batches:
            if b.project == batch_info.project:
                batch = b
                break

        if batch:
            if mode == "rev":
                revised_batch = Tm.Batch.objects.create(
                    uuid=uuid.uuid4(), user=batch_info.user,
                    revision_of=batch
                )
            batch_inputs = {i.hash: i for i in Tm.Input.objects.filter(batch=batch)}
            batch_labels = {l.hash: l for l in Tm.Label.objects.filter(batch=batch)}

            # Dealing with inputs
            inputs, processed_hashes = [], set()
            for input_type, changed_inputs in batch_info.inputs():
                for name, changed in changed_inputs.items():
                    if isinstance(changed, dict):
                        # this means we have changed a previous value
                        try:
                            inp = batch_inputs[changed['hash']]
                            processed_hashes.add(changed['hash'])
                            if inp.marker.code == name and inp.content != changed['value']:
                                inp.content = changed['value']
                                if mode == "rev":
                                    old_pk = inp.pk
                                    inp.pk = None
                                    inp.batch = revised_batch
                                    inp.revision_of_id = old_pk
                                    inp.revision_changes += "\nChanged {} [{}]".format(
                                        inp.marker.name,
                                        timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
                                    )
                                inputs.append(inp)
                        except KeyError:
                            # smth is wrong
                            pass
                    elif isinstance(changed, str):
                        # we create a value of a new parameter altogether
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

                            if mode == "e":
                                process_inputs(batch, batch_info, **kwargs)
                            elif mode == "rev":
                                process_inputs(revised_batch, batch_info, **kwargs)

            if inputs:
                if mode == "e":
                    Tm.Input.objects.bulk_update(inputs, ['content'])
                elif mode == "rev":
                    Tm.Input.objects.bulk_create(inputs)

            # Dealing with inputs that are deleted
            for ihash in batch_inputs:
                if ihash not in processed_hashes:
                    # means it was deleted
                    if mode == "e":
                        batch_inputs[ihash].delete()
                    elif mode == "rev":
                        revised_input = batch_inputs[ihash]
                        revised_input.content = ""
                        revised_input.pk = None
                        revised_input.batch = revised_batch
                        revised_input.revision_changes += "\nDeleted {} [{}]".format(
                            batch_inputs[ihash].marker.name,
                            timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
                        )
                        revised_input.save()

            # Dealing with labels
            for chunk in batch_info.chunks:
                if chunk.get('deleted', False):
                    chunk_hash = chunk.get('hash')
                    if chunk_hash and chunk_hash in batch_labels:
                        if mode == "e":
                            batch_labels[chunk_hash].delete()
                        elif mode == "rev":
                            revised_label = batch_labels[chunk_hash]
                            revised_label.pk = None
                            revised_label.batch = revised_batch
                            revised_label.undone = True
                            revised_label.revision_changes = "Deleted {}".format(batch_labels[chunk_hash].marker.name)
                            revised_label.save()

            if mode == "e":
                process_chunks_and_relations(batch, batch_info)
            elif mode == "rev":
                process_chunks_and_relations(revised_batch, batch_info)

            batch.save() # this updates dt_updated

            if mode != original_mode:
                mode = original_mode

            kwargs = {
                'current_uuid': batch.uuid,
                'template': 'partials/components/areas/_editing_body.html',
                'search_mv_pk': scope,
                'search_query': query
            }
            if mode == "rev":
                kwargs['template'] = 'partials/components/areas/_reviewing_body.html'
                try:
                    kwargs['ds_id'] = int(data['datasource'])
                    kwargs['dp_id'] = int(data['datapoint'])
                except Value:
                    kwargs['ds_id'], kwargs['dp_id'] = -1, -1

            return JsonResponse({
                'error': False,
                'mode': mode,
                'partial': True,
                'template': render_editing_board(
                    request, batch_info.project, batch_info.user, page,
                    **kwargs
                )
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
def recorded_search(request, proj):
    try:
        page = int(request.GET.get("p", 1))
        scope = int(request.GET.get("scope", -1))
        search_type = request.GET.get("search_type", "phr")
    except ValueError:
        page, scope = 1, -1
    query = request.GET.get("query", "")
    project = get_object_or_404(Tm.Project, pk=proj)

    return JsonResponse({
        'partial': True,
        'template': render_editing_board(
            request, project, request.user, page,
            search_mv_pk=scope,
            search_query=query,
            search_type=search_type,
            template='partials/components/areas/_editing_body.html'
        )
    })


@login_required
@require_http_methods(["GET"])
def editing(request, proj):
    page = int(request.GET.get("p", 1))
    project = get_object_or_404(Tm.Project, pk=proj)
    return JsonResponse({
        'partial': False,
        'template': render_editing_board(request, project, request.user, page)
    })


@login_required
@require_http_methods(["GET"])
def review(request, proj):
    try:
        ds = int(request.GET.get('ds', -1))
        dp = int(request.GET.get('dp', -1))
        page = int(request.GET.get("p", 1))
    except ValueError:
        ds, dp = -1, -1
        page = 1
    project = get_object_or_404(Tm.Project, pk=proj)
    return JsonResponse({
        'template': render_editing_board(
            request, project, request.user, page,
            template='partials/components/areas/reviewing.html',
            ds_id=ds, dp_id=dp
        )
    })


@login_required
@require_http_methods(["GET"])
def get_batch(request, proj):
    # TODO: ensure that the request cannot be triggered by external tools
    uuid = request.GET.get('uuid', '')
    if uuid:
        labels = Tm.Label.objects.filter(batch__uuid=uuid, marker__project_id=proj)
        inputs = Tm.Input.objects.filter(batch__uuid=uuid, marker__project_id=proj)

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

        flagged_datapoints = Tm.DataAccessLog.objects.filter(project=project).annotate(
            terrors=KeyTransform('text_errors', 'flags')
        ).exclude(terrors={}).exclude(terrors="").order_by('-dt_updated')
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
def flag_batch(request, proj):
    flag = request.POST.get('flag') == "true"
    batch_uuid = request.POST.get('uuid')

    try:
        project = Tm.Project.objects.filter(pk=proj).get()

        is_author, is_shared = project.author == request.user, project.shared_with(request.user)

        if is_author or is_shared:
            batches = Tm.Batch.objects.filter(uuid=batch_uuid).all()
        else:
            batches = Tm.Batch.objects.filter(
                uuid=batch_uuid, user=request.user
            ).all()

        for batch in batches:
            if batch and batch.project == project:
                batch.is_flagged = flag
                batch.save()
                return JsonResponse({
                    "errors": False
                })
        return JsonResponse({
            "errors": True
        })
    except Tm.Project.DoesNotExist:
        logger.error("Project does not exist")
    except Tm.Batch.DoesNotExist:
        logger.error("Batch does not exist")
    return JsonResponse({
        "errors": True
    })


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
