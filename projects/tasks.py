# -*- coding: utf-8 -*-
import bisect
from collections import defaultdict

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


@shared_task
def get_user_progress_stats(project_pk):
    logs = Tm.DataAccessLog.objects.filter(project__id=project_pk)
    submitted_logs = logs.filter(is_submitted=True)
    skipped_logs = logs.filter(is_skipped=True, is_submitted=False)

    submitted_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    skipped_logs_by_ds_and_user = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    dataset_info = {}
    l2i, i = {}, 0
    for logs_data, logs_storage in zip(
        [submitted_logs, skipped_logs],
        [submitted_logs_by_ds_and_user, skipped_logs_by_ds_and_user]):
        for l in logs_data:
            ds = l.datasource
            logs_storage[ds.pk][l.user.pk][l.datapoint].append(l)
            dataset_info[ds.pk] = {
                'size': ds.size(),
                'name': ds.name
            }
            if ds.pk not in l2i:
                l2i[ds.pk] = i
                i += 1
    x_axis = [dataset_info[k]['name'] for k in dataset_info]

    project = Tm.Project.objects.get(pk=project_pk)
    participants = project.participants
    N_participants = participants.count()

    if N_participants > 0:
        providers = [p.username for p in participants.all()]

        data = [[[0] * len(x_axis), [0] * len(x_axis)] for _ in range(N_participants)]
        p2i = {v.pk: k for k, v in enumerate(participants.all())}

        for logs_data, stack in zip([submitted_logs_by_ds_and_user, skipped_logs_by_ds_and_user], ['submitted', 'skipped']):
            for ds in logs_data:
                ds_logs = logs_data[ds]
                for u in ds_logs:
                    if stack == 'submitted':
                        data[p2i[u]][0][l2i[ds]] = round(len(ds_logs[u].keys()) * 100 / dataset_info[ds]['size'], 2)
                    else:
                        data[p2i[u]][1][l2i[ds]] = round(len(ds_logs[u].keys()) * 100 / dataset_info[ds]['size'], 2)

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
