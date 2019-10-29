import re
import json
import time
import uuid
import requests
from bs4 import BeautifulSoup, NavigableString


addresses = json.load(open('migrationsverket_urls'))['urls']


def get_text_from_printable(html_text):
    def get_text(text):
        if len(parts) > 0:
            return f'#{title}\n\n{text}'
        else:
            return text

    soup = BeautifulSoup(html_text, 'html.parser')

    parts = []
    text, num_elements, link_content = "", 0, ""
    header_start = 0 # where a new header have started

    title_tag, title = soup.find('title'), ''
    if title_tag:
        title += title_tag.text.strip().split('-')[0].strip()

    for div in soup.find_all('div', {'class': 'sv-text-portlet-content'}):
        parent = div.parent
        if parent.has_attr('class') and 'c41' in parent['class']:
            # handling "Fick du hjälp..." block
            continue

        for child in div:
            skip_adding = False
            if (child.has_attr('class') and 'ahjalpfunktioner' in child['class']) or (child.has_attr('id') and child['id'] == 'h-Migrationsverket'):
                # handling "Senast ändrad" and "Migrationsverket"
                continue

            if child.name in ['h1', 'h2', 'h3', 'p']:
                if child.name in ['h1', 'h2', 'h3']:
                    if len(text) - header_start < 50:
                        # we assume that the header is empty and delete it
                        text = text[:header_start]

                    header_start = len(text)
                    text += '#' * int(child.name[-1]) + ' '

                for tag in child:
                    num_elements += 1
                    if tag.name == 'br':
                        text += '\n'
                    elif type(tag) == NavigableString:
                        text += tag.strip()
                    else:
                        if tag.has_attr('class') and 'ahjalpfunktioner' in tag['class']:
                            continue

                        if tag.name == 'a':
                            if num_elements > 1:
                                text += link_content
                                text += " " + tag.text.strip()
                                link_content = ""
                            else:
                                link_content = " " + tag.text.strip()
                                skip_adding = True
                        else:
                            has_class = tag.has_attr('class')
                            if (has_class and 'circle-number' not in tag['class']) or not has_class:
                                text += tag.text.strip()
                            else:
                                skip_adding = True
                num_elements, link_content = 0, ""
            elif child.name in ['ul']:
                for tag in child:
                    text += f"\n* {tag.text}"
            else:
                continue
            if skip_adding: continue
            text = re.sub('[ ]{2,}', ' ', text.strip())
            text += "\n\n"
            if child.name == 'ul':
                text += "\n"

            if len(text.split()) > 400:
                if header_start > 0:
                    if len(text[:header_start].split()) > 200:
                        parts.append(get_text(text[:header_start].strip()))
                        text = text[header_start:]
                    else:
                        parts.append(get_text(text.strip()))
                        text = ""
                header_start = 0

    if len(text.split()) > 200:
        parts.append(get_text(text))

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

    # for part in get_text_from_printable(open('Ansöka om att förlänga besöket i Sverige - Migrationsverket.html').read()):
    #     print(part)
    #     print("\n===========\n")