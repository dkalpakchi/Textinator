import re
import pymongo
import mysql.connector
from WikiExtractor import Extractor, compact


# Some templates we're going to parse manually, e.g. {{formatnum:300}}
def replace_templates(wikitext):
    templates = re.findall(r'\{\{formatnum:[0-9\-\+\.\, |nt]+\}\}', wikitext)
    for temp in templates:
        num = temp.split(':')[1][:-2]
        num = num.split('|')[0] # if {{#formatnum: 2300.123|2}}, just ignore filters
        wikitext = wikitext.replace(temp, num)
    return wikitext


def test_wikitext():
    e = Extractor(None, None, '', [])
    wikitext = open('castillo.wiki').read()
    wikitext = replace_templates(wikitext)
    text = e.clean(e.wiki2text(e.transform(wikitext))).strip()
    print(text)

def test_parsed():
    text = open('parsed_article.txt').read()
    print(compact(text))

DB_NAME = 'svwiki'
DB_COLLECTION = 'articles'
mongoc = pymongo.MongoClient("mongodb://localhost:27017/")

dblist = mongoc.list_database_names()
if DB_NAME in dblist:
    print("The database {} exists.".format(DB_NAME))

mongo_svwiki = mongoc[DB_NAME]

colist = mongo_svwiki.list_collection_names()
if DB_COLLECTION in colist:
    print("The collection {} exists in the database {}.".format(DB_COLLECTION, DB_NAME))
mongo_articles = mongo_svwiki[DB_COLLECTION]


mysqlc = mysql.connector.connect(
  host="localhost",
  user="dmytro",
  passwd="Dmytro-777",
  database=DB_NAME
)

mysql_cur = mysqlc.cursor()
mysql_cur.execute("""
    SELECT page_id, page_title, old_text AS article FROM (
        SELECT page_title, page_latest, page_id FROM page 
        WHERE page_content_model = 'wikitext' AND page_namespace=0 AND page_is_redirect = 0 AND page_len > 10000
    ) pg INNER JOIN text ON page_latest = old_id;
    """)

e = Extractor(None, None, '', [])
for (page_id, page_title, old_text) in mysql_cur:
    if not page_title.startswith("Lista_"):
        text = e.clean(e.wiki2text(e.transform(replace_templates(old_text)))).strip()

        section, section_title = [], "Beginning"
        for line in compact(text):
            if line.startswith("Section::::"):
                # means new section
                section_text = "".join(section)
                if len(section_text) > 100:
                    mongo_articles.insert_one({
                        "page_id": page_id,
                        "page_title": page_title,
                        "section_title": section_title,
                        "text": section_text
                    })
                section, section_title = [], line.split("::::")[1]
            elif line:
                # means just a line
                section.append(line)
            else:
                section.append('\n\n')

        section_text = "".join(section)
        if len(section_text) > 100:
            mongo_articles.insert_one({
                "page_id": page_id,
                "page_title": page_title,
                "section_title": section_title,
                "text": section_text
            })
