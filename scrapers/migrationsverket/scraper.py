import json
import time
import uuid
import requests
from bs4 import BeautifulSoup


addresses = json.load(open('migrationsverket_urls'))['urls']


def get_text_from_printable(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    text = ""
    for div in soup.find_all('div', {'class': 'sv-text-portlet-content'}):
        for child in div:
            if child.name in ['h1', 'p']:
                for tag in child:
                    if not tag.name:
                        text += tag.strip()
                        text += '\n\n'
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