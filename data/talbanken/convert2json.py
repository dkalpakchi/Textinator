import os
import conllu
import json
import string

if __name__ == '__main__':
    data_file = open(os.path.join("raw", "sv_talbanken-ud-train.conllu"), "r", encoding="utf-8")
    # parse_incr is recommended for large files (more than 1 MB)
    # since it returns a generator, which is why a conversion to list
    docs, doc = [], {}
    for i, token_list in enumerate(conllu.parse_incr(data_file)):
        if 'newdoc id' in token_list.metadata:
            if doc:
                doc['raw'] = "\n\n".join([" ".join(p['sentences']) for p in doc['paragraphs']])
                docs.append(doc)
            doc = {
                'id': token_list.metadata['newdoc id'],
                'paragraphs': []
            }
        if 'newpar id' in token_list.metadata:
            doc['paragraphs'].append({
                'id': token_list.metadata['newpar id'],
                'sentences': []
            })
        text = token_list.metadata['text']
        if text[0] == '-':
            text = ">{}".format(text[1:])
        if text[-1] in string.punctuation:
            doc['paragraphs'][-1]['sentences'].append(text)
        else:
            doc['paragraphs'][-1]['sentences'].append("## {}\n\n".format(text))
    if doc and doc['paragraphs']:
        doc['raw'] = "\n\n".join([" ".join(p['sentences']) for p in doc['paragraphs']])
        docs.append(doc)
    json.dump(docs, open('sv_talbanken-ud-train.json', 'w'))
        