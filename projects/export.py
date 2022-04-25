import json
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
        'nodes': list(nodes.values()),
        'extra': group[0]['extra'],
        "annotator": group[0]['annotator']
    }

def group2hash(group):
    if type(group) == list:
        group = sorted(group, key=lambda x: x['first']['start'])
        return ";".join(["{}:{}:{}:{}:{}".format(
            x['type'], x['first']['start'], x['first']['end'],
            x['second']['start'], x['second']['end']
        ) for x in group])
    elif type(group) == dict:
        nodes = sorted(group['nodes'], key=lambda x: x['start'])
        return "{}:{}".format(group['type'], ";".join(["{},{}".format(x['start'], x['end']) for x in nodes]))


class Exporter:
    def __init__(self, project, config):
        self.__project = project
        self.__config = {
            'consolidate_clusters': False,
            'include_usernames': False
        }
        self.__config.update(config)

    def _export_corr(self):
        # The problem is that the context exists in every label and if this is the whole text, then it's a problem
        # So if the context is the whole text, we need to group by batches and send over contexts only once
        # Otherwise we'll need to have contexts for every label
        # We also skip non-relation labels for corr even if they exist
        json_exporter = 'to_short_rel_json'
        relations = LabelRelation.objects.filter(
            first_label__marker__project=self.__project, undone=False
        ).order_by('first_label__context_id', 'batch', 'cluster')

        grouped_relations = []
        labels_in_relation = set()
        is_bidirectional, hashes = {}, set()
        group, context, context_id, batch, cluster = [], None, -1, -1, -1
        for r in relations.prefetch_related('first_label', 'second_label', 'rule', 'batch'):
            if batch == -1 or r.batch != batch or r.cluster != cluster:
                if group:
                    if have_the_same_relation(group) and is_bidirectional.get(group[0]['type'], False):
                        group = merge2cluster(group)
                    ghash = group2hash(group)

                    if ghash not in hashes:
                        hashes.add(ghash)

                        if group not in grouped_relations[-1]["relations"].values():
                            grouped_relations[-1]["relations"]["{}_{}".format(batch, cluster)] = group
                group = []

            if context_id == -1 or context_id != r.first_label.context_id:
                if context_id == -1:
                    context_id = r.first_label.context_id
                    context = r.first_label.context.content
                else:
                    singletons = Label.objects.filter(
                        marker__project=self.__project,
                        context_id=context_id,
                        undone=False
                    ).exclude(pk__in=list(labels_in_relation))

                    if singletons.count():
                        grouped_relations[-1]["labels"] = []
                        for sng in singletons.all():
                            sng_obj = getattr(sng, json_exporter)()
                            if self.__config['include_usernames']:
                                sng_obj['annotator'] = sng.batch.user.username
                            grouped_relations[-1]["labels"].append(sng_obj)

                    labels_in_relation = set()
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
            if r.extra:
                group[-1]["extra"] = r.extra
            if self.__config['include_usernames']:
                group[-1]["annotator"] = r.batch.user.username
            batch = r.batch
            cluster = r.cluster
            context_id = r.first_label.context_id
            labels_in_relation.add(r.first_label.pk)
            labels_in_relation.add(r.second_label.pk)
            is_bidirectional[r.rule.name] = r.rule.direction == '2'
        else:
            if group:
                if have_the_same_relation(group) and is_bidirectional.get(group[0]['type'], False):
                    group = merge2cluster(group)
                ghash = group2hash(group)

                if ghash not in hashes:
                    hashes.add(ghash)

                    if group not in grouped_relations[-1]["relations"].values():
                        grouped_relations[-1]["relations"]["{}_{}".format(batch, cluster)] = group

            singletons = Label.objects.filter(
                marker__project=self.__project,
                context_id=context_id,
                undone=False
            ).exclude(pk__in=list(labels_in_relation))

            if singletons.count():
                grouped_relations[-1]["labels"] = []
                for sng in singletons.all():
                    sng_obj = getattr(sng, json_exporter)()
                    if self.__config['include_usernames']:
                        sng_obj['annotator'] = sng.batch.user.username
                    grouped_relations[-1]["labels"].append(sng_obj)
        return grouped_relations

    def _export_pronr(self):
        return self._export_corr()

    def _export_qa(self):
        inputs = Input.objects.filter(marker__project=self.__project).order_by('context_id')

        cur_context_id, lab_id = None, 0
        resp = []
        obj = None
        for inp in inputs.all():
            if cur_context_id != inp.context_id:
                if obj:
                    resp.append(obj)
                obj = {}
                obj["context"] = inp.context.content
                obj["annotations"] = []
            
            ann = {}
            inp_marker = (inp.marker.export_name or inp.marker.name_en.lower() or inp.marker.name.lower()) if inp.marker else "question"
            ann[inp_marker] = inp.content
            
            inp_labels = Label.objects.filter(batch=inp.batch).all()

            if inp_labels:
                ann["choices"] = []
                for label in inp_labels:
                    ann["choices"].append({
                        "text": label.text,
                        "start": label.start,
                        "end": label.end,
                        "type": label.marker.export_name or label.marker.name_en.lower() or label.marker.name.lower(),
                    })
                    if label.extra:
                        ann["choices"][-1]["extra"] = label.extra
                obj["annotations"].append(ann)

            cur_context_id = inp.context_id
        if obj:
            resp.append(obj)
        return resp

    def _export_mcqa(self):
        return self._export_qa()

    def _export_mcqar(self):
        input_batches = Input.objects.filter(marker__project=self.__project).values_list('batch', flat=True)
        batches = Batch.objects.filter(pk__in=input_batches).prefetch_related('label_set', 'input_set')

        resp = {}
        for batch in batches:
            inputs = batch.input_set

            if inputs.count():
                context_id = inputs.first().context_id
                if context_id not in resp:
                    resp[context_id] = {
                        "context": inputs.first().context.content,
                        "annotations": []
                    }

                if inputs.count():
                    resp[context_id]["annotations"].append([i.to_minimal_json() for i in inputs.all()])
        
        return list(resp.values())

    def _export_ner(self):
        label_batches = Label.objects.filter(
            marker__project=self.__project, undone=False
        ).values_list('batch', flat=True)

        batches = Batch.objects.filter(pk__in=label_batches).prefetch_related('label_set')
        resp = {}
        for batch in batches:
            labels = batch.label_set

            if labels.count():
                context_id = labels.first().context_id
                if context_id not in resp:
                    resp[context_id] = {
                        "context": labels.first().context.content,
                        "annotations": []
                    }

                ann = {}
                if labels.count():
                    ann["named_entities"] = [l.to_minimal_json() for l in labels.all()]
                
                resp[context_id]["annotations"].append(ann)
        return list(resp.values())

    def _export_mt(self):
        return self._export_mcqar()

    def _export_generic(self):
        if self.__config['consolidate_clusters']:
            return self._export_corr()
        else:
            label_batches = Label.objects.filter(
                marker__project=self.__project, undone=False
            ).values_list('batch', flat=True)
            input_batches = Input.objects.filter(
                marker__project=self.__project
            ).values_list('batch', flat=True)
            
            batches = Batch.objects.filter(pk__in=set(label_batches) | set(input_batches)).prefetch_related('label_set', 'input_set')
            resp = {}
            for batch in batches:
                labels = batch.label_set
                inputs = batch.input_set
                relations = batch.labelrelation_set

                if labels.count() or inputs.count():
                    context_id = inputs.first().context_id if inputs.count() else labels.first().context_id
                    if context_id not in resp:
                        resp[context_id] = {
                            "context": inputs.first().context.content if inputs.count() else labels.first().context.content,
                            "annotations": []
                        }

                    ann = {}
                    exclude_labels = set()
                    if relations.count():
                        ann["relations"] = []
                        for r in relations.all():
                            ann["relations"].append(r.to_minimal_json())
                            exclude_labels.add(r.first_label)
                            exclude_labels.add(r.second_label)

                    if labels.count():
                        ann["labels"] = [l.to_minimal_json() for l in labels.all() if l not in exclude_labels]
                        if not ann["labels"]:
                            del ann["labels"]

                    if inputs.count():
                        ann["inputs"] = [i.to_minimal_json() for i in inputs.all()]
                    
                    resp[context_id]["annotations"].append(ann)

        return list(resp.values())

    def export(self):
        return getattr(self, "_export_{}".format(self.__project.task_type))()