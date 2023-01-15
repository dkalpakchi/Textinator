# -*- coding: utf-8 -*-
import json
import uuid
import traceback

from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import F, Window, Subquery, OuterRef
from django.db.models.functions import RowNumber
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

import toolbox.string_combinator.models as SCm


# Create your views here.
@login_required
@require_http_methods(["GET"])
def index(request):
    return render(request, 'scombinator/index.html', {
        'transformations': [x.to_json() for x in SCm.StringTransformationRule.objects.filter(
            owner=request.user
        )],
        'banned': [x.value for x in SCm.FailedTransformation.objects.filter(
            transformation__owner=request.user
        )]
    })


@login_required
@require_http_methods(["POST"])
def record_transformation(request):
    op = request.POST.get('op')
    rule = json.loads(request.POST.get('rule'))
    res = {}

    if op == 'update':
        try:
            tsm = SCm.StringTransformationRule.objects.get(
                uuid = rule['uuid']
            )
            tsm.action = rule['action']
            tsm.s_from = rule['from']
            tsm.s_to = SCm.StringTransformationRule.DELIMETER.join(rule['to'])
            tsm.save()
            res['from'] = tsm.s_from
            res['uuid'] = tsm.uuid
        except SCm.StringTransformationRule.DoesNotExist:
            res['error'] = 'does_not_exist'
            traceback.print_exc()
        except SCm.StringTransformationRule.MultipleObjectsReturned as e:
            res['error'] = 'not_unique'
            traceback.print_exc()
    elif op == 'delete':
        SCm.StringTransformationRule.objects.filter(uuid=rule['uuid']).delete()
    else:
        uid = uuid.uuid4()
        SCm.StringTransformationRule.objects.create(
            action = rule['action'],
            s_from = rule['from'],
            s_to = SCm.StringTransformationRule.DELIMETER.join(rule['to']),
            owner = request.user,
            uuid = uid
        )
        res['from'] = rule['from']
        res['uuid'] = uid
    return JsonResponse(res)


@login_required
@require_http_methods(["POST"])
def record_generation(request):
    req_data = request.POST.get("data")
    batch = request.POST.get('batch')
    res = {
        'action': None
    }
    if req_data:
        data = json.loads(req_data)
        removed = json.loads(request.POST.get('removed'))
        if batch:
            obj, is_created = SCm.StringTransformationSet.objects.get_or_create(
                batch = batch,
                owner = request.user
            )
            obj.data = data
            obj.save()
            res['action'] = 'saved' if is_created else 'updated'
        else:
            obj = SCm.StringTransformationSet.objects.create(
                data = data,
                batch = uuid.uuid4(),
                owner = request.user
            )
            res['action'] = 'saved'
        if removed:
            for x in removed:
                SCm.FailedTransformation.objects.get_or_create(
                    transformation=obj, value=x
                )
        res['batch'] = obj.batch
    return JsonResponse(res);


@login_required
@require_http_methods(["GET"])
def search_generations(request):
    search_type = request.GET.get("search_type", "int")
    search_query = request.GET.get("query", "")

    search_types = {
        'int': 'plain',    # intersection
        'phr': 'phrase',   # phrase
        'web': 'websearch' # web-like
    }
    # TODO: make language-dependent
    search_config = "{}_lite".format('english')
    if search_query:
        vector = SearchVector("data", config=search_config)

        query = SearchQuery(
            search_query,
            search_type=search_types.get(search_type, search_types['int']),
            config=search_config
        )
        if search_query:
            if search_type == "phr":
                # phrase queries
                tr_sets = SCm.StringTransformationSet.objects.annotate(
                    search=vector
                ).filter(search=query)
            else:
                tr_sets = SCm.StringTransformationSet.objects.annotate(
                    rank=SearchRank(vector, query)
                ).filter(rank__gt=1e-3) # some of them get like 1e-20, which is why > 0 doesn't work'
    else:
        tr_sets = None
    return JsonResponse({
        "template": render_to_string(
            'scombinator/search_results.html', {
                "results": tr_sets
            }, request=request)
    });


@login_required
@require_http_methods(["GET"])
def load_generation(request):
    uid = request.GET.get("uuid")

    res = {
        'data': {}
    }
    if uid:
        tr_set = SCm.StringTransformationSet.objects.filter(batch=uid).first()
        res['data'] = tr_set.data
    return JsonResponse(res)
