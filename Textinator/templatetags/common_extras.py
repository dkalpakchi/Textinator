# -*- coding: utf-8 -*-
from django import template


register = template.Library()


@register.filter(name='subtract')
def subtract(value, arg):
    return value - arg


@register.filter
def divide(value, arg):
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None
