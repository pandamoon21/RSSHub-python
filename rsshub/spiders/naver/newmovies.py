import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    item['title'] = post['product']['meta']['name']
    imgurl = f"{post['product']['meta'].get('posterUrl')}?type=w320_r145"
    runtime = post['product']['meta']['screeningTimeMinute']
    age = post['product']['meta']['contentRating']['accessibleAge']
    star = post['product']['meta']['starScore']
    price = post["prices"][0]["price"]
    pricetype = post["prices"][0]["itemCategory"]
    link = f"https://serieson.naver.com/v2/movie/{post['viewSeq']}"
    item['description'] = "{}<br>{}<br>{}".format(
        "Score: {} | Runtime: {} | Age: {} | Price: {}₩ - {}".format(
            star, runtime, age, price, pricetype
        ),
        # post['product']['meta']['synopsis'],
        f"<a href='{link}'>Link contents</a>",
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    try:
        item['author'] = post['product']['meta'].get('directors', [])[0]
    except IndexError:
        item['author'] = "pandamoon21"
    timestamp_ms = post['product']['meta']['releaseTimestamp']
    item['pubDate'] = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https:/serieson.naver.com'})
    url = 'https://apis.naver.com/seriesOnWeb/serieson-web/v2/movie/products'
    posts = requests.get(
        url=url,
        params={
            "ero": False,
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
        'title': 'SeriesON Naver New Movies',
        'link': 'https://serieson.naver.com/v2/movie/products',
        'description': 'New Movies on Naver',
        'author': 'pandamoon21',
        'items': items
    }