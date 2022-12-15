# -*- coding: utf-8 -*-
from celery import shared_task

import projects.models as Tm


@shared_task
def get_label_length_stats(project_pk):
    labels = Tm.Label.objects.filter(marker__project__id=project_pk, undone=False).all()
    inputs = Tm.Input.objects.filter(marker__project__id=project_pk).all()
    x_axis = sorted(set([len(l.text.split()) for l in labels]) | set([len(i.content.split()) for i in inputs]))
    project = Tm.Project.objects.get(pk=project_pk)
    participants = project.participants.all()

    data = [[0] * len(x_labels) for _ in range(project.markers.count())]
    l2i = {v: k for k, v in enumerate(x_axis)}
    p2i = {v.name: k for k, v in enumerate(project.markers.all())}

    for source in [labels, inputs]:
        for l in source:
            if hasattr(l, 'text'):
                data[p2i[l.marker.marker.name]][l2i[len(l.text.split())]] += 1
            elif hasattr(l, 'content'):
                data[p2i[l.marker.marker.name]][l2i[len(l.content.split())]] += 1
    return {
        'x_axis': x_axis,
        'plot_data': data,
        'providers': [m.name for m in project.markers.all()]
    }
