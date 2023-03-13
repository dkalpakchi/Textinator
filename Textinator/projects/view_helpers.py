# -*- coding: utf-8 -*-
import json
import numbers
from collections import defaultdict, OrderedDict

from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import F, Window, Subquery, OuterRef
from django.db.models.functions import RowNumber
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.utils import timezone

from .models import *


class BatchInfo:
    def __init__(self, data, proj, user, mode):
        self.chunks = json.loads(data['chunks'])
        self.relations = json.loads(data['relations'])
        self.marker_groups = json.loads(data["marker_groups"], object_pairs_hook=OrderedDict)
        self.short_text_markers = json.loads(data['short_text_markers'])
        self.long_text_markers = json.loads(data['long_text_markers'])
        self.numbers = json.loads(data['numbers'])
        self.ranges = json.loads(data['ranges'])
        self.text_markers = json.loads(data['text_markers'])
        self.radios = json.loads(data['radio'])
        self.checkboxes = json.loads(data['checkboxes'])
        self.datapoint = str(data['datapoint'])
        self.context = data.get('context').replace("\r\n", "\n")

        try:
            self.project = Project.objects.get(pk=proj)
        except Project.DoesNotExist:
            self.project = None

        try:
            self.data_source = DataSource.objects.get(pk=data['datasource'])
        except DataSource.DoesNotExist:
            self.data_source = None

        self.user = user

    def inputs(self):
        return [
            ('short_text_markers', self.short_text_markers),
            ('long_text_markers', self.long_text_markers),
            ('numbers', self.numbers),
            ('ranges', self.ranges),
            ('radios', self.radios),
            ('checkboxes', self.checkboxes)
        ]


def listify(x):
    return x if isinstance(x, list) else [x]

def get_or_create_ctx(batch_info, ctx_cache):
    if ctx_cache:
        ctx = retrieve_by_hash(batch_info.context, Context, ctx_cache)
        if not ctx:
            ctx = Context.objects.create(
                datasource=batch_info.data_source,
                datapoint=batch_info.datapoint,
                content=batch_info.context
            )
            ctx_cache.set(ctx.content_hash, ctx.pk, 3600)
    else:
        ctx, _ = Context.objects.get_or_create(
            datasource=batch_info.data_source,
            datapoint=batch_info.datapoint,
            content=batch_info.context
        )
    return ctx


def process_chunk(chunk, batch, batch_info, caches, ctx_cache=None):
    saved_labels = 0

    if chunk.get('marked', False) and (not chunk.get('deleted', False)) and chunk.get('updated', True):
        ctx_cache, label_cache = caches

        ctx = get_or_create_ctx(batch_info, ctx_cache)

        try:
            if (not 'label' in chunk) or (not isinstance(chunk['label'], str)):
                return (ctx_cache, label_cache), saved_labels

            chunk_label = chunk['label'].strip()
            code = "_".join(chunk_label.split("_")[:-1])
            # TODO: check interaction with MarkerUnits
            markers = MarkerVariant.objects.filter(project=batch_info.project, marker__code=code)

            marker = None
            for mv in markers:
                if mv.code == chunk_label:
                    marker = mv
                    break
        except MarkerVariant.DoesNotExist:
            return (ctx_cache, label_cache), saved_labels

        if 'lengthBefore' in chunk and 'start' in chunk and 'end' in chunk and marker:
            new_start = chunk['lengthBefore'] + chunk['start']
            new_end = chunk['lengthBefore'] + chunk['end']

            # it's fine if input is blank
            new_label = Label.objects.create(
                context=ctx, start=new_start, end=new_end, marker=marker,
                batch=batch, extra={k: v for k, v in chunk['extra'].items() if v}
            )
            new_label.revision_changes = "Added a new marker of type {} [{}]".format(
                marker.name,
                timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
            )
            label_cache[chunk['id']] = new_label.id
            saved_labels += 1
        return (ctx_cache, label_cache), saved_labels


def extract_ids(batches):
    if batches:
        batch_ids = batches.values_list('batch_id', flat=True)
    else:
        batch_ids = []

    return batch_ids


def verbalize_search_type(st):
    if st == "int":
        return "plain" # intersection query
    elif st == "phr":
        return "phrase" # phrase query
    elif st == "web":
        return "websearch" # web-like search with OR allowed

def check_empty(var, default):
    ban = set()
    if var is None:
        var = default
    else:
        for i, x in enumerate(var):
            # to accommodate possibilities of 0-indexes
            if not x and not isinstance(x, numbers.Number):
                ban.add(i)
    return var, ban

def get_unbanned(lst, ban):
    return [x for i, x in enumerate(lst) if i not in ban]

def render_editing_board(request, project, user, page, template='partials/components/areas/editing.html', ds_id=None, dp_id=None,
                         current_uuid=None, search_dict=None):
    is_author, is_shared = project.author == user, project.shared_with(user)

    if search_dict is None:
        search_mv_pks, search_queries, search_types = [], [], []
    else:
        # TODO: if this every becomes a speed bottleneck, which I doubt
        #       re-write and make a linear scan out of it
        search_mv_pks, ban_mv = check_empty(search_dict['scope'], [])
        search_queries, ban_q = check_empty(search_dict['query'], [])
        search_types, ban_t = check_empty(search_dict['search_type'], ["phr"])
        ban = set.union(ban_mv, ban_q, ban_t)

        search_mv_pks = get_unbanned(search_mv_pks, ban)
        search_queries = get_unbanned(search_queries, ban)
        search_types = get_unbanned(search_types, ban)

    if is_author or is_shared:
        label_batches = Label.objects.filter(marker__project=project).order_by('dt_created')
        input_batches = Input.objects.filter(marker__project=project).order_by('dt_created')
    else:
        label_batches = Label.objects.filter(batch__user=user, marker__project=project).order_by('dt_created')
        input_batches = Input.objects.filter(batch__user=user, marker__project=project).order_by('dt_created')

    label_batch_ids, input_batch_ids = extract_ids(label_batches), extract_ids(input_batches)

    # Here we don't use just dataset identifiers, because
    # there can, of course, be multiple datasets with the same
    # datapoint IDs
    window_exp = Window(
        expression=RowNumber(),
        order_by=F('dt_created').asc()
    )

    relevant_batches = Batch.objects.filter(
        pk__in=set(label_batch_ids) | set(input_batch_ids)
    ).annotate(index=window_exp)

    if -2 in search_mv_pks:
        # search for specific annotation no.
        sq_id = search_mv_pks.index(-2)
        search_query = search_queries[sq_id]

        sql_string, sql_params = relevant_batches.query.sql_with_params()
        search_indices = [int(x) for x in search_query.strip().split(",") if x.strip()]
        batches = Batch.objects.raw(
            "SELECT * FROM ({}) t1 WHERE t1.index IN ({}) ORDER BY t1.dt_created DESC NULLS LAST;".format(
                sql_string, ", ".join(["%s" for _ in range(len(search_indices))])
            ),
            list(sql_params) + search_indices
        )
    else:
        if ds_id and dp_id:
            # reviewing
            if ds_id > 0 and dp_id > 0:
                label_batches = label_batches.filter(
                    context__datasource_id=ds_id,
                    context__datapoint=dp_id
                )
                input_batches = input_batches.filter(
                    context__datasource_id=ds_id,
                    context__datapoint=dp_id
                )
            else:
                label_batches, input_batches = None, None

        lang_dict = dict(settings.LANGUAGES)
        sconf_dict = settings.LANG_SEARCH_CONFIG
        search_config = sconf_dict.get(
            project.language,
            lang_dict.get(project.language, 'english')
        ).lower()

        vector = None
        if search_mv_pks or search_queries:
            input_batch_ids = []
            for search_mv_pk, search_query, search_type in zip(search_mv_pks, search_queries, search_types):
                search_mv_pk = int(search_mv_pk)
                if search_mv_pk is not None:
                    if search_mv_pk == 0:
                        vector = "context__content_vector"
                        input_batches_clause = input_batches
                    else:
                        # -2 means search by annotation number
                        vector = SearchVector("content", config=search_config)

                    if search_mv_pk > 0:
                        input_batches_clause = input_batches.filter(marker_id=search_mv_pk)
                    elif search_mv_pk == -3:
                        # means search only among flagged
                        input_batches_clause = input_batches.filter(batch__is_flagged=True)
                    elif search_mv_pk == -1:
                        input_batches_clause = input_batches


                if search_query and vector:
                    query = SearchQuery(
                        search_query,
                        search_type=verbalize_search_type(search_type),
                        config=search_config
                    )

                    if search_type == "phr":
                        # phrase queries
                        if isinstance(vector, str):
                            input_batches_clause = input_batches_clause.filter(**{vector: query}) # some of them get like 1e-20, which is why > 0 doesn't work'
                        else:
                            input_batches_clause = input_batches_clause.annotate(
                                search=vector
                            ).filter(search=query) # some of them get like 1e-20, which is why > 0 doesn't work'
                    else:
                        input_batches_clause = input_batches_clause.annotate(
                            rank=SearchRank(vector, query)
                        ).filter(rank__gt=1e-3) # some of them get like 1e-20, which is why > 0 doesn't work'
                ib_ids = extract_ids(input_batches_clause)
                input_batch_ids.append(set(ib_ids))

            batch_ids = set.intersection(*input_batch_ids) if input_batch_ids else set()
        else:
            batch_ids = set(label_batch_ids) | set(input_batch_ids)

        if batch_ids:
            sql_string, sql_params = relevant_batches.query.sql_with_params()
            batches = Batch.objects.raw(
                "SELECT * FROM ({}) t1 WHERE t1.id IN ({}) ORDER BY t1.dt_created DESC NULLS LAST;".format(
                    sql_string, ", ".join(["%s" for _ in range(len(batch_ids))])
                ),
                list(sql_params) + [str(x) for x in list(batch_ids)]
            )
        else:
            batches = []

    p = Paginator(batches, 30)

    return render_to_string(template, {
        'paginator': p,
        'page': page,
        'project': project,
        'is_admin': is_author or is_shared,
        'current_uuid': current_uuid
    }, request=request)


def process_inputs(batch, batch_info, short_text_markers=None, long_text_markers=None,
    numbers=None, ranges=None, radios=None, checkboxes=None, ctx_cache=None):
    if any([short_text_markers, long_text_markers, numbers, ranges, radios, checkboxes]):
        stm, ltm, num, ran = short_text_markers, long_text_markers, numbers, ranges
        rad, check = radios, checkboxes
    else:
        stm = batch_info.short_text_markers
        ltm = batch_info.long_text_markers
        num = batch_info.numbers
        ran = batch_info.ranges
        rad = batch_info.radios
        check = batch_info.checkboxes
    inputs = [stm, ltm, num, ran, rad, check]

    if any(inputs):
        new_inputs = [x for x in inputs if x]

        ctx = get_or_create_ctx(batch_info, ctx_cache)

        mv = {}
        for inp_type in new_inputs:
            for code, inp_string in inp_type.items():
                if inp_string.strip():
                    marker_code = "_".join(code.split("_")[:-1])
                    if marker_code not in mv:
                        marker_variants = MarkerVariant.objects.filter(
                            project=batch_info.project,
                            marker__code=marker_code
                        )
                        mv[marker_code] = marker_variants

                    for m in mv[marker_code]:
                        if m.code == code:
                            Input.objects.create(
                                content=inp_string.strip(),
                                marker=m,
                                batch=batch,
                                context=ctx
                            )
                            break


def process_chunks_and_relations(batch, batch_info, ctx_cache=None):
    saved_labels = 0
    label_cache = {}
    for chunk in batch_info.chunks:
        # inp is typically the same for all chunks
        res_chunk = process_chunk(
            chunk, batch, batch_info,
            (ctx_cache, label_cache)
        )
        if res_chunk:
            ret_caches, just_saved = res_chunk
            ctx_cache, label_cache = ret_caches
            saved_labels += just_saved

    for i, rel in enumerate(batch_info.relations):
        for link in rel['links']:
            source_id, target_id = int(link['s']), int(link['t'])

            try:
                source_label = Label.objects.filter(pk=label_cache.get(source_id, -1)).get()
                target_label = Label.objects.filter(pk=label_cache.get(target_id, -1)).get()
            except Label.DoesNotExist:
                continue

            try:
                rule = RelationVariant.objects.filter(pk=rel['rule']).get()
            except RelationVariant.DoesNotExist:
                continue

            LabelRelation.objects.create(
                rule=rule, first_label=source_label, second_label=target_label, batch=batch,
                cluster=i+1, extra=rel['extra']
            )


def process_marker_groups(batch, batch_info, ctx_cache=None):
    if batch_info.marker_groups:
        marker_groups = OrderedDict()
        for k, v in batch_info.marker_groups.items():
            name_parts = k.split("_")
            unit, i, mv_code = name_parts[0], name_parts[1], "_".join(name_parts[2:-1])
            prefix = "{}_{}".format(unit, i)
            if prefix not in marker_groups:
                marker_groups[prefix] = defaultdict(list)
            if v:
                if isinstance(v, list):
                    marker_groups[prefix][mv_code].extend(v)
                else:
                    marker_groups[prefix][mv_code].append(v)

        if len([a for x in marker_groups.values() for y in x.values() for a in y]) > 0:
            ctx = get_or_create_ctx(batch_info, ctx_cache)

            mv_map = {}
            for i, (prefix, v) in enumerate(marker_groups.items()):
                unit_cache = []
                for code, values in v.items():
                    marker_code = "_".join(code.split("_")[:-1])
                    if marker_code not in mv_map:
                        marker_variants = MarkerVariant.objects.filter(
                            project=batch_info.project, marker__code=marker_code
                        )
                        mv_map[marker_code] = marker_variants

                    mv = None
                    for m in mv_map[marker_code]:
                        if m.code == code:
                            mv = m
                            break

                    unit = prefix.split("_")[0]

                    if mv.unit.name != unit:
                        continue

                    N = sum(map(bool, values))
                    if N >= mv.min() and N <= mv.max():
                        for val in values:
                            if val:
                                unit_cache.append({
                                    'content': val,
                                    'marker': mv,
                                    'group_order': i + 1
                                })
                    else:
                        unit_cache = []
                        break

                for dct in unit_cache:
                    if dct['marker'].is_free_text():
                        Input.objects.create(context=ctx, batch=batch, **dct)


def process_text_markers(batch, batch_info, text_markers=None, ctx_cache=None):
    sent_text_markers = text_markers or batch_info.text_markers

    if sent_text_markers:
        ctx = get_or_create_ctx(batch_info, ctx_cache)

        mv = {}
        for tm_code in sent_text_markers:
            marker_code = "_".join(tm_code.split("_")[:-1])
            if marker_code not in mv:
                marker_variants = MarkerVariant.objects.filter(project=batch_info.project, marker__code=marker_code)
                mv[marker_code] = marker_variants

            for m in mv[marker_code]:
                if m.code == tm_code:
                    Label.objects.create(context=ctx, marker=m, batch=batch)
                    break


def follow_json_path(obj, path):
    if len(path) == 0:
        yield obj
        return

    ARRAY_MARKER = "[ ]"
    if path[0] == ARRAY_MARKER:
        if not isinstance(obj, list): return
        for x in obj:
            batch = []
            for r in follow_json_path(x, path[1:]):
                batch.append(r)
            yield batch[0] if len(batch) == 1 else batch
    elif path[0] in obj:
        yield from follow_json_path(obj[path[0]], path[1:])
    else:
        return


def process_recorded_search_args(request_dict):
    try:
        page = int(request_dict.get("p", 1))
        scope = request_dict.get("scope")
        search_type = request_dict.get("search_type")
    except ValueError:
        page, scope = 1, -1
    query = request_dict.get("query")

    if scope is None:
        scope = list(map(int, request_dict.getlist("scope[]", [])))
    else:
        scope = int(scope)

    if search_type is None:
        search_type = request_dict.getlist("search_type[]", "phr")

    if query is None:
        query = request_dict.getlist("query[]", "")

    # Scope:
    # -1 -- Everything except text (flagged or annotation no.)
    # -2 -- Annotation no.
    # -3 -- Limit to flagged only
    return {
        'page': page,
        'search_dict': {
            'scope': listify(scope),
            'query': listify(query),
            'search_type': listify(search_type)
        }
    }
