import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    time_broad_ms = post['product']['meta']['broadcastStartTimestamp']
    time_broad = datetime.fromtimestamp(time_broad_ms / 1000).strftime('%d-%m-%Y')
    item['title'] = "{} - {}".format(post['product']['meta']['name'], time_broad)
    item['description'] = "{a}<br>{b}".format(
        a=post['product']['meta']['synopsis'],
        b=f"<img referrerpolicy='no-referrer' src={post['product']['meta'].get('posterUrl')}>"
    )
    item['link'] = f"https://serieson.naver.com/v2/broadcasting/{post['viewSeq']}"
    try:
        item['author'] = post['product']['meta'].get('directors', [])[0]
    except IndexError:
        pass
    timestamp_ms = post['product']['meta']['releaseTimestamp']
    item['pubDate'] = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https:/serieson.naver.com'})
    import json
    url = 'https://apis.naver.com/seriesOnWeb/serieson-web/v1/season/recommend/products'
    posts = requests.get(
        url=url,
        params={
            "offset": "0",
            "limit": "31",
            "_t": int(time.time()) * 1000
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['result']['productList']
    items = list(map(parse, posts))
    return {
        'title': 'SeriesON Naver New Series',
        'link': 'https://serieson.naver.com/v2/season/products/recommend',
        'description': 'New Series on Naver',
        'author': 'pandamoon21',
        'items': items
    }