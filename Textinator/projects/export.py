# -*- coding: utf-8 -*-
from collections import abc

from django.db.models import F, Window
from django.db.models.functions import RowNumber

from .models import *


# Taken from:
# https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
def dict_update(d, u):
    for k, v in u.items():
        if isinstance(v, abc.Mapping):
            d[k] = dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


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
        'extra': group[0]['extra'] if 'extra' in group[0] else '',
        "annotator": group[0]['annotator'] if 'annotator' in group[0] else ''
    }


def group2hash(group):
    if isinstance(group, list):
        group = sorted(group, key=lambda x: x['first']['start'])
        return ";".join(["{}:{}:{}:{}:{}".format(
            x['type'], x['first']['start'], x['first']['end'],
            x['second']['start'], x['second']['end']
        ) for x in group])
    elif isinstance(group, dict):
        nodes = sorted(group['nodes'], key=lambda x: x['start'])
        return "{}:{}".format(group['type'], ";".join(["{},{}".format(x['start'], x['end']) for x in nodes]))


class AnnotationExporter:
    def __init__(self, project, config):
        self.__project = project
        self.__config = {
            'consolidate_clusters': False,
            'include_usernames': False,
            'include_batch_no': False,
            'include_flags': False
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

            if context_id == -1 or (
                context_id != r.first_label.context_id and
                context == r.first_label.context.content):
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

        cur_context_id = None
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

            if self.__config['include_batch_no']:
                window_exp = Window(
                    expression=RowNumber(),
                    order_by=F('dt_created').asc()
                )
                batches = batches.annotate(index=window_exp)

            resp = {}
            for batch in batches:
                labels = batch.label_set
                inputs = batch.input_set
                relations = batch.labelrelation_set

                if labels.count() or inputs.count():
                    context_id = inputs.first().context_id if inputs.count() else labels.first().context_id

                    if context_id not in resp:
                        ctx = inputs.first().context if inputs.count() else labels.first().context
                        resp[context_id] = {
                            "context": ctx.content,
                            "annotations": []
                        }
                        if self.__config["include_flags"]:
                            resp[context_id]["flags"] = {}
                            dals = DataAccessLog.objects.filter(
                                datapoint=ctx.datapoint, datasource_id=ctx.datasource_id,
                                is_deleted=False
                            )
                            for dal in dals.all():
                                resp[context_id]['flags'] = dict_update(
                                    resp[context_id]['flags'], dal.flags
                                )
                        if self.__config["include_batch_no"]:
                            resp[context_id]["num"] = batch.index

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

                    if self.__config["include_usernames"]:
                        ann["annotator"] = batch.user.username

                    resp[context_id]["annotations"].append(ann)
        return list(resp.values())

    def export(self):
        return getattr(self, "_export_{}".format(self.__project.task_type))()


class ProjectSettingsExporter:
    def __init__(self, proj):
        self.__proj = proj
        self.__settings_fields = (
                'data_order', 'is_open', 'allow_selecting_labels', 'disable_submitted_labels',
                'disjoint_annotation', 'auto_text_switch', 'allow_editing', 'editing_as_revision',
                'allow_reviewing', 'editing_title_regex'
        )

        self.__task_spec = ('task_type', 'modal_configs')

    def export(self):
        data = {
            'settings': {},
            'task_spec': {},
            'markers': {},
            'relations': {}
        }

        for setting in self.__settings_fields:
            data['settings'][setting] = getattr(self.__proj, setting)

        for task_spec in self.__task_spec:
            data['task_spec'][task_spec] = getattr(self.__proj, task_spec)

        for marker in self.__proj.markers.all():
            data['markers'].append(marker.to_json())

        for relation in self.__proj.relations.all():
            data['relations'].append(relation)

        return data
