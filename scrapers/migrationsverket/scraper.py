import json
import time
import uuid
import requests
from bs4 import BeautifulSoup, NavigableString


addresses = json.load(open('migrationsverket_urls'))['urls']


def get_text_from_printable(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    text = ""
    for div in soup.find_all('div', {'class': 'sv-text-portlet-content'}):
        for child in div:
            if child.name in ['h1', 'p']:
                for tag in child:
                    if type(tag) == NavigableString:
                        text += child.text
                        text += '\n\n'
                    else:
                        has_class = tag.has_attr('class')
                        if tag.name != 'a' and ((has_class and 'circle-number' not in tag['class']) or not has_class):
                            text += child.text
                            text += '\n\n'
            elif child.name in ['ul']:
                text = text[:-1] # remove \n\n
                for tag in child:
                    text += u"\u2022"
                    text += f" {tag.text}\n"
                text += "\n\n"

    return text.strip()

def crawl(url):
    res = requests.get("{}.printable".format(url))
    return res.text



if __name__ == '__main__':
    for url in addresses:
        json.dump({
            'url': url,
            'text': get_text_from_printable(crawl(url))
        }, open('migrationsverket_{}.json'.format(uuid.uuid4().hex), 'w'))
