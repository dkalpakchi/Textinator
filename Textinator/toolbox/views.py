# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from .apps import TOOLS
from .decorators import toolbox_required

@login_required
@toolbox_required
@require_http_methods(["GET"])
def index(request):
    return render(request, 'toolbox/index.html', {
        'tools': TOOLS
    })
