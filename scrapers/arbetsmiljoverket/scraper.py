import re
import json
import uuid
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString


BASE_URL = "https://www.av.se"
addresses = json.load(open('urls'))['urls']


def get_text(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    parts = []
    text, num_elements, link_content = "", 0, ""
    header_start = 0 # where a new header have started

    prohibited = set(["updated", "rs_skip", "commentboxblock", "share-box", "onpagenavigation"])

    for div in soup.find_all('main', {'id': 'main'}):
        search_through = list(div.children)
        for tag in search_through:
            if type(tag) == NavigableString or type(tag) == str:
                text += tag.strip()
            elif tag.name in ['a']:
                continue
            elif tag.name in ['ul', 'ol']:
                for i, pchild in enumerate(tag):
                    if type(pchild) == NavigableString or type(pchild) == str:
                        if pchild.strip():
                            text += f"{'*' if tag.name == 'ul' else i+1} {pchild.strip()}\n"
                    else:
                        text += f"{'*' if tag.name == 'ul' else i+1} {pchild.text.strip()}\n"
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
            elif tag.name == 'div' and (not tag.has_attr('class') or \
                (tag.has_attr('class') and (not (set(tag.attrs['class']) & prohibited)))):
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
            if part:
                json.dump({
                    'url': url,
                    'text': part
                }, open(f'arbetsmiljoverket_{url_hex}_p{i}.json', 'w'))

    # for part in get_text(open('För dig som är lärare | Elsäkerhetsverket.html').read()):
    #     print(part)
    #     print("\n===========\n")