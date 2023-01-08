# -*- coding: utf-8 -*-
from modeltranslation.translator import translator, TranslationOptions
from .models import Marker, Relation


class MarkerTranslationOptions(TranslationOptions):
    fields = ('name',)


class RelationTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Marker, MarkerTranslationOptions)
translator.register(Relation, RelationTranslationOptions)
