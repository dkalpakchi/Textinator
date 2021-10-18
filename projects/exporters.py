from collections import OrderedDict, defaultdict

from .models import *


def have_the_same_relation(group):
    return len(set([r['type'] for r in group])) == 1

def merge2cluster(group):
    nodes = {}
    for r in group:
        nodes["{}:{}".format(r['first']['start'], r['first']['end'])] = r['first']
        nodes["{}:{}".format(r['second']['start'], r['second']['end'])] = r['second']
    return {
        'type': group[0]['type'],
        'nodes': list(nodes.values())
    }

def group2hash(group):
    if type(group) == list:
        group = sorted(group, key=lambda x: x['first']['start'])
        return ";".join(["{}:{}:{}:{}:{}:{}".format(
            x['type'], x['first']['start'], x['first']['end'],
            x['second']['start'], x['second']['end'], x['first']['user']
        ) for x in group])
    elif type(group) == dict:
        nodes = sorted(group['nodes'], key=lambda x: x['start'])
        return "{}:{}".format(group['type'], ";".join(["{},{}".format(x['start'], x['end']) for x in nodes]))

def export_corr(project):
    # The problem is that the context exists in every label and if this is the whole text, then it's a problem
    # So if the context is the whole text, we need to group by batches and send over contexts only once
    # Otherwise we'll need to have contexts for every label
    # We also skip non-relation labels for corr even if they exist
    is_paragraph_context = project.context_size == 'p'
    json_exporter = 'to_rel_json' if is_paragraph_context else 'to_short_rel_json'
    relations = LabelRelation.objects.filter(first_label__marker__project=project, undone=False).order_by('first_label__context_id', 'batch')

    grouped_relations = {} if is_paragraph_context else []
    is_bidirectional, hashes = {}, set()
    group, context, context_id, batch = [], None, -1, -1
    for r in relations.prefetch_related('first_label', 'second_label', 'rule', 'batch'):
        if batch == -1 or r.batch != batch:
            if group:
                if have_the_same_relation(group) and is_bidirectional.get(group[0]['type'], False):
                    group = merge2cluster(group)
                ghash = group2hash(group)

                if ghash not in hashes:
                    hashes.add(ghash)

                    if is_paragraph_context:
                        grouped_relations[str(batch)] = {
                            'context': context,
                            'relations': group
                        }
                    else:
                        if group not in grouped_relations[-1]["relations"].values():
                            grouped_relations[-1]["relations"][str(batch)] = group
            group = []

        if context_id == -1 or context_id != r.first_label.context_id:
            if context_id == -1:
                context_id = r.first_label.context_id
                context = r.first_label.context.content
            if not is_paragraph_context:
                context = r.first_label.context.content
                grouped_relations.append({
                    'context': context,
                    "relations": {}
                })

        group.append({
            'type': r.rule.name,
            'first': getattr(r.first_label, json_exporter)(),
            'second': getattr(r.second_label, json_exporter)()
        })
        batch = r.batch
        context_id = r.first_label.context_id
        is_bidirectional[r.rule.name] = r.rule.direction == '2'
    else:
        if group:
            if have_the_same_relation(group) and is_bidirectional.get(group[0]['type'], False):
                group = merge2cluster(group)
            ghash = group2hash(group)

            if ghash not in hashes:
                hashes.add(ghash)

                if is_paragraph_context:
                    grouped_relations[str(batch)] = {
                        'context': context,
                        'relations': group
                    }
                else:
                    if group not in grouped_relations[-1]["relations"].values():
                        grouped_relations[-1]["relations"][str(batch)] = group
    return grouped_relations


def export_qa(project):
    labels = Label.objects.filter(marker__project=project, undone=False).order_by('batch')
    N = labels.count()
    batches = labels.values_list('batch').distinct()
    inputs = Input.objects.filter(batch__in=batches).order_by('batch')
    labels = list(labels.all())

    lab_id = 0
    resp = []
    for inp in inputs.all():
        obj = {}
        obj["context"] = inp.context.content
        obj[inp.marker.name if inp.marker else "question"] = inp.content
        
        inp_labels = []
        while lab_id < N and labels[lab_id].batch == inp.batch:
            inp_labels.append(labels[lab_id])
            lab_id += 1

        if inp_labels:
            obj["choices"] = []
            for label in inp_labels:
                obj["choices"].append({
                    "text": label.text,
                    "start": label.start,
                    "end": label.end,
                    "type": label.marker.marker.name,
                    "extra": label.extra,
                    "context": label.context.content
                })
            resp.append(obj)
    return resp


def export_generic(project):
    labels = Label.objects.filter(project=project, undone=False).order_by('context_id').distinct()
    resp = []
    groups, group, batch, context_id, context = {}, [], None, -1, None
    for l in labels:
        if batch is None or batch != l.batch:
            if group:
                groups[str(batch)] = group
                group = []
            batch = l.batch
        if context_id == -1 or context_id != l.context_id:
            if groups:
                resp.append({
                    'context': context.content,
                    'labels': groups
                })
                groups = {}
            context_id = l.context_id
            context = l.context
        dct = l.to_short_rel_json()
        del dct['batch']
        group.append(dct)
    else:
        if group:
            groups[str(batch)] = group
        if groups:
            resp.append({
                'context': context.content,
                'labels': groups
            })
    return resp
