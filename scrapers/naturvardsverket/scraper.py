import re
import json
import uuid
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString


BASE_URL = "https://www.naturvardsverket.se"
addresses = json.load(open('naturvardsverket_urls'))['urls']


def get_text(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    parts = []
    text, num_elements, link_content = "", 0, ""
    header_start = 0 # where a new header have started

    header = soup.find('p', {'class': 'preamble'})
    title = ''
    if header:
        for sib in header.previous_siblings:
            if type(sib) != str and type(sib) != NavigableString:
                if sib.name == 'h1':
                    title = sib.text.strip()
                    break
    
    for div in soup.find_all('div', {'class': 'body with-related'}):
        for inner_div in div:
            for tag in inner_div:
                if type(tag) == NavigableString or type(tag) == str:
                    text += tag.strip()
                elif tag.name in ['a', 'ul']:
                    continue
                elif tag.name == 'p':
                    text += re.sub('[ ]{2,}', ' ', tag.text.replace('\n', ' ').strip()) + "\n\n"
                elif tag.name == 'h2':
                    header_start = len(text)
                    text += f'## {tag.text.strip()}\n\n'

                if len(text.split()) > 400:
                    parts.append(f'# {title}\n\n{text[:header_start]}')
                    text = text[header_start:]
    
    if len(text.split()) > 200:
        parts.append(f'# {title}\n\n{text}')
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
            }, open(f'naturvardsverket_{url_hex}_p{i}.json', 'w'))

    # for part in get_text(open('Miljökvalitetsmålet Begränsad klimatpåverkan - Naturvårdsverket.html').read()):
    #     print(part)
    #     print("\n===========\n")