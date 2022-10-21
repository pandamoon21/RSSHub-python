import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    time_broad_ms = post['product']['meta']['broadcastStartTimestamp']
    time_broad = datetime.fromtimestamp(time_broad_ms / 1000).strftime('%d-%m-%Y')
    item['title'] = "{} - {}".format(post['product']['meta']['name'], time_broad)
    imgurl = f"{post['product']['meta'].get('posterUrl')}?type=w320_r145"
    runtime = post['product']['meta']['screeningTimeMinute']
    age = post['product']['meta']['contentRating']['accessibleAge']
    price = post["singlePrices"][0]["price"]
    priceseason = post["seasonPrices"][0]["price"]
    item['description'] = "{a}<br>{b}<br>{c}".format(
        a="Runtime: {} | Age: {} | Price: {}₩ (single) - {}₩ (season)".format(
            runtime, age, price, priceseason
        ),
        b=post['product']['meta']['synopsis'],
        c=f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = f"https://serieson.naver.com/v2/broadcasting/{post['viewSeq']}"
    try:
        item['author'] = post['product']['meta'].get('directors', [])[0]
    except IndexError:
        item['author'] = "pandamoon21"
    timestamp_ms = post['product']['meta']['releaseTimestamp']
    item['pubDate'] = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https:/serieson.naver.com'})
    url = 'https://apis.naver.com/seriesOnWeb/serieson-web/v2/season/products'
    posts = requests.get(
        url=url,
        params={
            "ero": False,
            "category": "KOREAN",
            # "end": False,
            "orderType": "RECENT_REGISTRATION",
            "offset": 0,
            "limit": 31,
            "_t": int(time.time()) * 1000
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['result']['productList']
    items = list(map(parse, posts))
    return {
        'title': 'SeriesON Naver New Drama',
        'link': 'https://serieson.naver.com/v2/broadcasting/products',
        'description': 'New Drama on Naver',
        'author': 'pandamoon21',
        'items': items
    }