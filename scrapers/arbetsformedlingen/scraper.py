import re
import json
import time
import uuid
import requests # does not work for some reason
from urllib.parse import urljoin
import html2markdown


BASE_URL = "https://arbetsformedlingen.se"
addresses = json.load(open('urls'))['urls']


##
## Gets the text.
##
## :param      prof:  The object describing a profession
## :type       prof:  dict
##
## :returns:   The plain description text for the work to be performed and education needed for this profession
## :rtype:     dict
##
def get_text(prof):
    return {
        'id': prof['amsOccupationId'],
        'profession': prof['namn'],
        'work': html2markdown.convert(prof['beskrivning']['arbete']),
        'education': html2markdown.convert(prof['beskrivning']['utbildning'])
    }


def crawl(url):
    res = requests.get(urljoin(BASE_URL, url), allow_redirects=False)
    return res.json()


if __name__ == '__main__':
    for url in addresses:
        res = get_text(crawl(url))
        for tp in ['work', 'education']:
            if len(res[tp].split()) > 200:
                json.dump({
                    'text': f'## {res["profession"]}\n\n{res[tp]}'
                }, open(f'af_{res["id"]}_{tp}.json', 'w'))