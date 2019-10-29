import re
import json
import uuid
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString


BASE_URL = "https://www.elsakerhetsverket.se"
addresses = json.load(open('elsakerhetsverket_urls'))['urls']


def get_text(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    parts = []
    text, num_elements, link_content = "", 0, ""
    header_start = 0 # where a new header have started

    for div in soup.find_all('div', {'id': 'maincontent'}):
        search_through = list(div.children)
        for tag in search_through:
            if type(tag) == NavigableString or type(tag) == str:
                text += tag.strip()
            elif tag.name in ['a', 'ul']:
                continue
            elif tag.name == 'p':
                for pchild in tag:
                    if pchild.name != 'a':
                        if type(pchild) == NavigableString or type(pchild) == str:
                            text += re.sub('[ ]{2,}', ' ', pchild.replace('\n', ' ').strip()) + "\n\n"
                        else:
                            text += re.sub('[ ]{2,}', ' ', pchild.text.replace('\n', ' ').strip()) + "\n\n"
            elif tag.name in ['h2', 'h1']:
                header_start = len(text)
                size = int(tag.name[-1])
                text += '#' * size + f' {tag.text.strip()}\n\n'
            elif tag.name == 'div':
                search_through.extend(tag.children)
                continue

            if len(text.split()) > 400:
                parts.append(text[:header_start])
                text = text[header_start:]

    if len(text.split()) > 200:
        parts.append(text)
    return parts

def crawl(url):
    res = requests.get(urljoin(BASE_URL, url))
    return res.text


if __name__ == '__main__':
    for url in addresses:
        url_hex = uuid.uuid4().hex
        for i, part in enumerate(get_text(crawl(url))):
            json.dump({
                'url': url,
                'text': part
            }, open(f'elsakerhetsverket_{url_hex}_p{i}.json', 'w'))

    # for part in get_text(open('För dig som är lärare | Elsäkerhetsverket.html').read()):
    #     print(part)
    #     print("\n===========\n")