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