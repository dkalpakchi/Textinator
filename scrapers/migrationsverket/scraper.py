import json
import time
import uuid
import requests
from bs4 import BeautifulSoup, NavigableString


addresses = json.load(open('migrationsverket_urls'))['urls']


def get_text_from_printable(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    parts = []
    text, num_elements, link_content = "", 0, ""
    header_start = 0 # where a new header have started
    for div in soup.find_all('div', {'class': 'sv-text-portlet-content'}):
        for child in div:
            if child.name in ['h1', 'h2', 'h3', 'p']:
                if child.name == 'h1':
                    header_start = len(text)
                    text += '# '
                elif child.name == 'h2':
                    header_start = len(text)
                    text += '## '

                for tag in child:
                    num_elements += 1
                    if type(tag) == NavigableString:                        
                        text += tag.strip()
                    else:
                        if tag.name == 'a':
                            if num_elements > 1:
                                text += link_content
                                text += tag.text.strip()
                                link_content = ""
                            else:
                                link_content = tag.text.strip()
                        else:
                            has_class = tag.has_attr('class')
                            if (has_class and 'circle-number' not in tag['class']) or not has_class:
                                text += tag.text
                num_elements, link_content = 0, ""
            elif child.name in ['ul']:
                for tag in child:
                    text += u"\u2022"
                    text += f" {tag.text}\n"
            text = text.strip()
            text += "\n\n"

            if len(text.split()) > 400:
                if header_start > 0:
                    parts.append(text[:header_start].strip())
                    text = text[header_start:]
                header_start = 0

    if len(text.split()) < 100 and len(parts) > 0:
        parts[-1] += text
    else:
        parts.append(text)

    return parts

def crawl(url):
    res = requests.get("{}.printable".format(url))
    return res.text



if __name__ == '__main__':
    for url in addresses:
        url_hex = uuid.uuid4().hex
        for i, part in enumerate(get_text_from_printable(crawl(url))):
            json.dump({
                'url': url,
                'text': part
            }, open(f'migrationsverket_{url_hex}_p{i}.json', 'w'))