# -*- coding: utf-8 -*-
import json
import uuid
import traceback

from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

import toolbox.string_combinator.models as SCm


# Create your views here.
@login_required
@require_http_methods(["GET"])
def index(request):
    return render(request, 'string_combinator.html', {
        'transformations': [x.to_json() for x in SCm.StringTransformation.objects.filter(
            owner=request.user
        )]
    })

@login_required
@require_http_methods(["POST"])
def record(request):
    op = request.POST.get('op')
    rule = json.loads(request.POST.get('rule'))
    res = {}
    print(op)

    if op == 'update':
        try:
            tsm = SCm.StringTransformation.objects.get(
                uuid = rule['uuid']
            )
            tsm.action = rule['action']
            tsm.s_from = rule['from']
            tsm.s_to = SCm.StringTransformation.DELIMETER.join(rule['to'])
            tsm.save()
            res['from'] = tsm.s_from
            res['uuid'] = tsm.uuid
        except SCm.StringTransformation.DoesNotExist:
            res['error'] = 'does_not_exist'
            traceback.print_exc()
        except SCm.StringTransformation.MultipleObjectsReturned as e:
            res['error'] = 'not_unique'
            traceback.print_exc()
    elif op == 'delete':
        SCm.StringTransformation.objects.filter(uuid=rule['uuid']).delete()
    else:
        uid = uuid.uuid4()
        SCm.StringTransformation.objects.create(
            action = rule['action'],
            s_from = rule['from'],
            s_to = SCm.StringTransformation.DELIMETER.join(rule['to']),
            owner = request.user,
            uuid = uid
        )
        res['from'] = rule['from']
        res['uuid'] = uid
    return JsonResponse(res)
