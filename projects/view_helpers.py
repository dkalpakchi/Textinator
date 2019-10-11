from .models import *


def process_chunk(chunk, batch, data_input, project, user, caches, booleans):
    saved_labels = 0
    if chunk.get('marked', False):
        ctx_cache, inp_cache, label_cache = caches
        is_resolution, is_review = booleans

        if 'context' in chunk and type(chunk['context']) == str:
            ctx = retrieve_by_hash(chunk['context'], Context, ctx_cache)
            if not ctx:
                ctx = Context.objects.create(content=chunk['context'])
                ctx_cache.set(ctx.content_hash, ctx.pk, 600)
        else:
            ctx = None

        try:
            if (not 'label' in chunk) or (type(chunk['label']) != str):
                return (ctx_cache, inp_cache, label_cache), saved_labels
            marker = Marker.objects.get(name=chunk['label'].strip())
        except Marker.DoesNotExist:
            return (ctx_cache, inp_cache, label_cache), saved_labels

        if data_input:
            inp = retrieve_by_hash(data_input, Input, inp_cache)
            if not inp:
                inp = Input.objects.create(context=ctx, content=data_input)
                inp_cache.set(inp.content_hash, inp.pk, 600)
        else:
            inp = None

        if 'lengthBefore' in chunk and 'start' in chunk and 'end' in chunk:
            new_start = chunk['lengthBefore'] + chunk['start']
            new_end = chunk['lengthBefore'] + chunk['end']

            if is_resolution:
                # resolution case
                pass
            elif is_review:
                # check if matches original answer
                if inp:
                    original = Label.objects.filter(input=inp).get()
                else:
                    original = Label.objects.filter(context=ctx).get()

                if original:
                    ambiguity_status, is_match = 'no', False
                    no_overlap = (original.start > new_end) or (original.end < new_start)
                    
                    if not no_overlap:
                        is_match = (original.start == new_start) and (original.end == new_end)
                        if not is_match:
                            requires_resolution = (original.start == new_start) or (original.end == new_end)
                            if requires_resolution:
                                ambiguity_status = 'rr'
                    
                    LabelReview.objects.create(
                        original=original, start=new_start, end=new_end, user=user, marker=marker,
                        ambiguity_status=ambiguity_status, is_match=is_match
                    )
            else:
                if inp:
                    new_label = Label.objects.create(
                        input=inp, start=new_start, end=new_end, marker=marker, user=user, project=project, batch=batch
                    )
                else:
                    new_label = Label.objects.create(
                        context=ctx, start=new_start, end=new_end, marker=marker, user=user, project=project, batch=batch
                    )
                label_cache[chunk['id']] = new_label.id
                saved_labels += 1
    return (ctx_cache, inp_cache, label_cache), inp, saved_labels