# -*- coding: utf-8 -*-
import bisect
from collections import defaultdict, Counter

from django.db.models import Count

from celery import shared_task

import projects.models as Tm


def get_chartjs_datasets(providers, data):
    datasets = []
    for label, items in zip(providers, data):
        datasets.append({
            "label": label,
            "data": items
        })
    return datasets

def count_token_lengths(items, item_type):
    prop = 'text' if item_type == 'label' else 'content'
    counts = defaultdict(lambda: defaultdict(int))
    lengths = set()
    for item in items.all():
        text = getattr(item, prop)
        N_tokens = len(text.split())
        counts[item.marker.marker.name][N_tokens] += 1
        lengths.add(N_tokens)
    return counts, lengths

@shared_task
def get_label_lengths_stats(project_pk):
    project = Tm.Project.objects.get(pk=project_pk)
    participants = project.participants.all()

    labels = Tm.Label.objects.filter(
            marker__project__id=project_pk,
            marker__anno_type='m-span',
            undone=False
    )
    inputs = Tm.Input.objects.filter(
            marker__project__id=project_pk,
            marker__anno_type__in=['free-text', 'lfree-text']
    )

    lab_counts, lab_lengths = count_token_lengths(labels, 'label')
    inp_counts, inp_lengths = count_token_lengths(inputs, 'input')
    x_axis = sorted(lab_lengths | inp_lengths)
    marker_names = sorted(set(lab_counts.keys()) | set(inp_counts.keys()))
    N_markers = len(marker_names)

    data = [[0] * len(x_axis) for _ in range(N_markers)]
    l2i = {v: k for k, v in enumerate(x_axis)}
    p2i = {v: k for k, v in enumerate(marker_names)}

    for marker_counts in [lab_counts, inp_counts]:
        for mn, counts in marker_counts.items():
            for length, count in counts.items():
                data[p2i[mn]][l2i[length]] = count

    return {
        'labels': x_axis,
        'datasets': get_chartjs_datasets(marker_names, data)
    }

@shared_task
def get_user_timings_stats(project_pk):
    inputs = Tm.Input.objects.filter(
        marker__project__id=project_pk
    ).order_by('dt_created').all()

    labels = Tm.Label.objects.filter(
        marker__project__id=project_pk, undone=False
    ).order_by('dt_created').all()

    inputs_by_user = defaultdict(lambda: defaultdict(list))
    labels_by_user = defaultdict(lambda: defaultdict(list))
    for inp in inputs:
        inputs_by_user[inp.batch.user.username][str(inp.batch)].append(inp)
    for lab in labels:
        labels_by_user[lab.batch.user.username][str(lab.batch)].append(lab)

    timings = []
    for arr in [inputs_by_user, labels_by_user]:
        for u in arr:
            ll = list(arr[u].items())
            for b1, b2 in zip(ll[:len(ll)], ll[1:]):
                l1, l2 = b1[1][0], b2[1][0]
                if l1 and l2 and l1.dt_created and l2.dt_created and\
                    l1.dt_created.month == l2.dt_created.month and\
                    l1.dt_created.day == l2.dt_created.day and\
                    l1.dt_created.year == l2.dt_created.year:
                    timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1) # in minutes
                    if timing > 0 and timing < 120:
                        # if timing is 0, means they were simply a part of the same batch
                        # timing < 60 is simply a precaution
                        timings.append(timing)

    x_axis = []
    if timings:
        min_time, max_time = int(min(timings)), int(round(max(timings)))
        x_axis = list(range(min_time, max_time, 1))
        if x_axis:
            x_axis.append(x_axis[-1] + 1)

    project = Tm.Project.objects.get(pk=project_pk)
    participants = project.participants
    N_participants = participants.count()

    if N_participants > 0:
        providers = [p.username for p in participants.all()]

        data = [[0] * len(x_axis) for _ in range(N_participants)]
        p2i = {v.username: k for k, v in enumerate(participants.all())}

        for arr in [inputs_by_user, labels_by_user]:
            for u in arr:
                ll = list(arr[u].items())
                for b1, b2 in zip(ll[:len(ll)], ll[1:]):
                    l1, l2 = b1[1][0], b2[1][0]
                    if l1 and l2 and l1.dt_created and l2.dt_created:
                        timing = round((l2.dt_created - l1.dt_created).total_seconds() / 60., 1)
                        if timing > 0 and timing < 120:
                            pos = bisect.bisect(x_axis, timing)
                            data[p2i[u]][pos - 1] += 1

        return {
            'labels': x_axis,
            'datasets': get_chartjs_datasets(providers, data)
        }
    else:
        return {}

def logs2dict(logs):
    progress_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))

    for l in logs:
        progress_counts[l['is_submitted']][l['is_skipped']][l['datasource']][l['user_id']] = l['datapoint__count']

    return progress_counts

@shared_task
def get_user_progress_stats(project_pk):
    project = Tm.Project.objects.get(pk=project_pk)
    participants = project.participants
    N_participants = participants.count()

    logs = Tm.DataAccessLog.objects.filter(
        project_id=project_pk
    ).values(
        'datasource', 'user_id', 'is_submitted', 'is_skipped'
    ).annotate(Count('datapoint'))
    progress_counts = logs2dict(logs)

    dataset_info = {
        ds.pk: {'size': ds.size(), 'name': ds.name}
        for ds in project.datasources.all()
    }
    x_axis = [v['name'] for v in dataset_info.values()]
    N_categories = len(x_axis)

    if N_participants > 0:
        providers = [p.username for p in participants.all()]

        data = [[[0] * N_categories, [0] * N_categories] for _ in range(N_participants)]
        l2i = {pk: i for i, pk in enumerate(dataset_info.keys())}
        p2i = {v.pk: k for k, v in enumerate(participants.all())}

        for stack in ['submitted', 'skipped']:
            if stack == 'submitted':
                logs_data, proc_ds = {}, set()
                for ds in progress_counts[True][False]:
                    c = Counter()
                    c.update(progress_counts[True][False][ds])
                    c.update(progress_counts[True][True][ds])
                    logs_data[ds] = c
                    proc_ds.add(ds)

                for ds in progress_counts[True][True]:
                    if ds not in proc_ds:
                        logs_data[ds] = progress_counts[True][True][ds]
            else:
                logs_data = progress_counts[False][True]
            for ds in logs_data:
                ds_logs = logs_data[ds]
                for u in ds_logs:
                    if stack == 'submitted':
                        data[p2i[u]][0][l2i[ds]] = round(ds_logs[u] * 100 / dataset_info[ds]['size'], 2)
                    else:
                        data[p2i[u]][1][l2i[ds]] = round(ds_logs[u] * 100 / dataset_info[ds]['size'], 2)

        series = []
        for i, d in enumerate(data):
            series.append({
                "label": providers[i] + '_submitted',
                "data": d[0],
                'stack': providers[i]
            })
            series.append({
                "label": providers[i] + '_skipped',
                "data": d[1],
                'stack': providers[i]
            })
        return {
            'labels': x_axis,
            'datasets': series
        }
    else:
        return {}

@shared_task
def get_data_source_sizes_stats(project_pk):
    project = Tm.Project.objects.get(pk=project_pk)
    x_axis = list(project.datasources.values_list('name', flat=True))
    providers = ['Number of datapoints']
    sizes = [[p.size() for p in project.datasources.all()]]
    return {
        "labels": x_axis,
        "datasets": get_chartjs_datasets(providers, sizes)
    }
