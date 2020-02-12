from collections import OrderedDict

from .models import *


def export_corr(project):
    label_relations = LabelRelation.objects.filter(project=project, undone=False).order_by('-dt_created')

    relations = OrderedDict()
    for lr in label_relations:
        fst, snd = lr.first_label, lr.second_label
        if fst.context.pk in relations:
            relations[fst.context.pk].append((fst, snd))
        else:
            relations[fst.context.pk] = [(fst, snd)]

    resp = []
    for cpk, rels in relations.items():
        obj = {}
        context = Context.objects.get(pk=cpk)
        obj["context"] = context.content
        obj["coref"] = []
        for fst, snd in rels:
            obj["coref"].append({
                "pronoun": { "text": fst.text, "start": fst.start, "end": fst.end },
                "antecedent": { "text": snd.text, "start": snd.start, "end": snd.end }
            })
        resp.append(obj)
    return resp


def export_qa(project):
    inputs_pks = Label.objects.filter(project=project, undone=False).values_list('input', flat=True).distinct()
    inputs = Input.objects.filter(pk__in=inputs_pks).order_by('-dt_created').all()
    labeled_inputs = [
        (inp, Label.objects.filter(input=inp, undone=False).all())
        for inp in inputs
    ]

    resp = []
    for inp, labels in labeled_inputs:
        obj = {}
        obj["context"] = inp.context.content
        obj["question"] = inp.content
        obj["choices"] = []
        for label in labels:
            obj["choices"].append({
                "text": label.text,
                "start": label.start,
                "end": label.end,
                "type": label.marker.name,
                "comment": label.comment
            })
        resp.append(obj)
    return resp