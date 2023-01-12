# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.
def string_combinator(request):
    return render(request, 'string_combinator.html')
