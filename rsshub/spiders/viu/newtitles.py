import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def get_date(rls_date):
    date = "{}-{}-{} {}:{}:{}".format(
        rls_date[:4], rls_date[5:7], rls_date[8:10],
        rls_date[11:13], rls_date[14:16], rls_date[17:19]
    )
    return date

def parse(post):
    item = {}
    title_type = "movie" if post['is_movie'] == 1 else "series"
    judul = post['series_name'] if title_type == "series" else post['title']
    episode = post.get('number', None)
    totaleps = post.get('released_product_total')
    if episode:
        judul += f" E{int(episode):02}"
    category = post.get('category_name')
    judul += f" - {title_type.upper()}"
    synopsis = post.get('synopsis')
    item['title'] = judul
    imgurl1 = post['cover_image_url']
    imgurl2 = post['series_image_url']
    link_path = "{}/{}".format(
        post['id'],
        post['series_name'].replace(" ", "-").replace("(", "").replace(")", "").strip()
    )
    link = f"https://www.viu.com/ott/sg/en-us/vod/{link_path}"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}".format(
        a=f"Category: {category} - Synopsis: {synopsis} - Total Eps: {totaleps}",
        b=f"<a href='{link}'>Link contents</a>",
        c=f"<img referrerpolicy='no-referrer' src='{imgurl2}'>",
        d=f"<img referrerpolicy='no-referrer' src='{imgurl1}'>"
    )
    item['link'] = link
    # item['pubDate'] = datetime.fromtimestamp(int(time.time()) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item


def ctx():
    DEFAULT_HEADERS.update({
        "Origin": "https://viu.com",
        "Referer": "https://viu.com/",
    })
    url = 'https://www.viu.com/ott/sg/index.php'
    posts = requests.get(
        url=url,
        headers={
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-forwarded-for': '193.56.255.18'  #  bypass SG ip restriction
        },
        params={
            "r": "listing/ajax",
            "platform_flag_label": "web",
            "area_id": "2",
            "language_flag_id": "3",
            "cpreference_id": "",
            "grid_id": "202013"
        }
    )
    posts = posts.json()['data']['series']
    items = list(map(parse, posts))
    return {
        'title': 'VIU SG New Titles',
        'link': 'https://www.viu.com/ott/sg/',
        'description': 'New Titles on VIU SG',
        'author': 'pandamoon21',
        'items': items
    }