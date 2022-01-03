from .models import *
from django.template.loader import render_to_string
from django.db.models import F


def process_chunk(chunk, batch, project, data_source, datapoint, user, caches):
    saved_labels = 0
    if chunk.get('marked', False):
        ctx_cache, label_cache = caches

        # First check for the "context", there may be 2 cases:
        # a) the context is the whole text, in which case it's already created as input_context previously and will be just retrieved from cache
        # b) the context is something other than the whole text, in which case it will be created here
        if 'context' in chunk and type(chunk['context']) == str:
            ctx = retrieve_by_hash(chunk['context'], Context, ctx_cache)
            if not ctx:
                ctx = Context.objects.create(datasource=data_source, datapoint=datapoint, content=chunk['context'])
                ctx_cache.set(ctx.content_hash, ctx.pk, 600)
        else:
            ctx = None

        try:
            if (not 'label' in chunk) or (type(chunk['label']) != str):
                return (ctx_cache, label_cache), saved_labels
            marker_obj = Marker.objects.get(code=chunk['label'].strip())
            # TODO: check interaction with MarkerUnits
            marker = MarkerVariant.objects.filter(project=project, marker=marker_obj).first()
        except Marker.DoesNotExist:
            return (ctx_cache, label_cache), saved_labels

        if 'lengthBefore' in chunk and 'start' in chunk and 'end' in chunk:
            new_start = chunk['lengthBefore'] + chunk['start']
            new_end = chunk['lengthBefore'] + chunk['end']

            # it's fine if input is blank
            new_label = Label.objects.create(
                context=ctx, start=new_start, end=new_end, marker=marker,
                batch=batch, extra={k: v for k, v in chunk['extra'].items() if v}
            )
            label_cache[chunk['id']] = new_label.id
            saved_labels += 1
        return (ctx_cache, label_cache), saved_labels


def render_editing_board(project, user):
    label_batches = Label.objects.filter(batch__user=user, marker__project=project).values_list('batch__uuid', flat=True)
    input_batches = Input.objects.filter(batch__user=user, marker__project=project).values_list('batch__uuid', flat=True)

    batch_uuids = set(label_batches) | set(input_batches)
    batches = Batch.objects.filter(uuid__in=batch_uuids).order_by(F('dt_updated').desc(nulls_last=True), '-dt_created')

    return render_to_string('partials/components/areas/editing.html', {
        'batches':batches,
        'project': project
    })

def process_free_text_inputs(free_text_inputs, batch, project, data_source, datapoint, input_context, ctx_cache=None):
    if ctx_cache:
        ctx = retrieve_by_hash(input_context, Context, ctx_cache)
        if not ctx:
            ctx = Context.objects.create(datasource=data_source, datapoint=str(datapoint), content=input_context)
            ctx_cache.set(ctx.content_hash, ctx.pk, 3600)
    else:
        ctx = Context.objects.get(datasource=data_source, datapoint=str(datapoint), content=input_context)
    
    mv = {}
    for code, inp_string in free_text_inputs.items():
        marker_code = "_".join(code.split("_")[:-1])
        if marker_code not in mv:
            marker_variants = MarkerVariant.objects.filter(project=project, marker__code=marker_code)
            mv[marker_code] = marker_variants

        for m in mv[marker_code]:
            if m.code == code:
                Input.objects.create(content=inp_string, marker=m, batch=batch, context=ctx)
                break