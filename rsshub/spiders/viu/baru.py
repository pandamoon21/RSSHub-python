import base64
import hashlib
import requests
import time

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from rsshub.utils import DEFAULT_HEADERS
from tinydb import TinyDB, Query
from typing import List

viudb = Path(__file__).parent.joinpath('viubaru_db.json')
viubaru_DB = TinyDB(str(viudb))

class HTMLTableParser(HTMLParser):
    """ This class serves as a html table parser. It is able to parse multiple
    tables which you feed in. You can access the result per .tables field.
    """
    def __init__(
        self,
        decode_html_entities: bool = False,
        data_separator: str = ' ',
    ) -> None:

        HTMLParser.__init__(self, convert_charrefs=decode_html_entities)

        self._data_separator = data_separator

        self._in_td = False
        self._in_th = False
        self._current_table = []
        self._current_row = []
        self._current_cell = []
        self.tables = []
        self.named_tables = {}
        self.name = ""

    def handle_starttag(self, tag: str, attrs: List) -> None:
        """ We need to remember the opening point for the content of interest.
        The other tags (<table>, <tr>) are only handled at the closing point.
        """
        if tag == "table":
            name = [a[1] for a in attrs if a[0] == "id"]
            if len(name) > 0:
                self.name = name[0]
        if tag == 'td':
            self._in_td = True
        if tag == 'th':
            self._in_th = True

    def handle_data(self, data: str) -> None:
        """ This is where we save content to a cell """
        if self._in_td or self._in_th:
            self._current_cell.append(data.strip())
    
    def handle_endtag(self, tag: str) -> None:
        """ Here we exit the tags. If the closing tag is </tr>, we know that we
        can save our currently parsed cells to the current table as a row and
        prepare for a new row. If the closing tag is </table>, we save the
        current table and prepare for a new one.
        """
        if tag == 'td':
            self._in_td = False
        elif tag == 'th':
            self._in_th = False

        if tag in ['td', 'th']:
            final_cell = self._data_separator.join(self._current_cell).strip()
            self._current_row.append(final_cell)
            self._current_cell = []
        elif tag == 'tr':
            self._current_table.append(self._current_row)
            self._current_row = []
        elif tag == 'table':
            self.tables.append(self._current_table)
            if len(self.name) > 0:
                self.named_tables[self.name] = self._current_table
            self._current_table = []
            self.name = ""


def check_db(judul_hash):
    return bool(viubaru_DB.contains(Query().judul_hash == judul_hash))

def table_2_list(xhtml, limit):
    p = HTMLTableParser()
    p.feed(xhtml)

    tables = p.tables               # Get all tables
    tables_list = tables[0][1:]     # exclude table name
    if limit:
        return tables_list[:limit]      # apply limit
    else:
        return tables_list

def parse(post):
    item = {}
    judul = post[6]
    judul_hash = hashlib.md5(judul.strip().encode()).hexdigest()
    item['title'] = judul.strip()
    total_vid = post[8]
    language = post[10]
    genre = post[11]
    cp_name = post[5]
    geo_right = post[-1]
    item['description'] = "{}<br>{}<br>{}<br>{}<br>{}<br>{}".format(
        f'Title     : {judul.strip()}',
        f'Genre     : {genre}',
        f'Language  : {language}',
        f'CP Name   : {cp_name}',
        f'Total Vid : {total_vid}',
        f'Geo Right : {geo_right}'
    )
    item['author'] = "pandamoon21"
    tanggal = datetime.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S')
    if check_db(judul_hash):
        item['pubDate'] = viubaru_DB.search(Query().judul_hash == judul_hash)[0]["date"]
    else:
        viubaru_DB.insert({
            'judul_hash': judul_hash,
            'date': tanggal
        })
        item['pubDate'] = tanggal
    return item


def ctx(limit='0'):
    url = 'aHR0cHM6Ly9wYXJ0bmVyLnZ1Y2xpcC5jb20vaW5nZXN0aW9uL2NoYW5uZWxKc3A='
    posts = requests.get(
        url=base64.b64decode(url).decode("utf-8"),
        headers=DEFAULT_HEADERS
    )
    limit = int(limit)
    posts_list = table_2_list(posts.text, limit)
    items = list(map(parse, posts_list))
    items = [x for x in items if x]
    return {
        'title': 'VIU Baru',
        'link': "https://www.viu.com",
        'description': 'VIU Baru',
        'author': 'pandamoon21',
        'items': items
    }