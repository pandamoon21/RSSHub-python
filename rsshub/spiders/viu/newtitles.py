import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def get_date(rls_date):
    # 28-06-2022
    date = "{}-{}-{} 00:00:01".format(
        rls_date[-4:], rls_date[3:5], rls_date[:2]
    )
    return date

def clean_name(name):
    name = name.replace(" ", "-").replace("(", "").replace(")", "").replace(
        "!", "").replace(":", "").strip()
    return name

def parse(post):
    item = {}
    title_type = "movie" if post['is_movie'] == 1 else "series"
    if title_type == "movie":
        return item
    judul = post['name']
    episode = post.get('number', 1)
    totaleps = post.get('released_product_total', '-')
    if episode:
        judul += f" - E{int(episode):02}"
    # judul += f" - {title_type.upper()}"
    # synopsis = post.get('synopsis')
    item['title'] = judul
    imgurl1 = post.get('cover_landscape_image_url', post.get('cover_image_url'))
    imgurl2 = post['series_image_url']
    imgurl3 = post.get('product_image_url')
    link_path = "{}/{}".format(
        post.get('product_id', post.get('id', '')),
        clean_name(post['name'])
    )
    # https://www.viu.com/ott/sg/en/vod/2227298/Unbreak-My-Heart
    cp_name = post.get('cp_name')
    category = post.get('category_name')
    item['cat'] = category
    link = f"https://www.viu.com/ott/sg/en-us/vod/{link_path}"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}".format(
        a=f"CP Name: {cp_name} - Total Eps: {totaleps}",
        b=f"<a href='{link}'>Link contents</a>",
        c=f"<img referrerpolicy='no-referrer' src='{imgurl1}'>",
        d=f"<img referrerpolicy='no-referrer' src='{imgurl3}'>"
    )
    item['link'] = link
    # item['pubDate'] = datetime.fromtimestamp(int(time.time()) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item


def ctx(region='', category=''):
    DEFAULT_HEADERS.update({
        "Origin": "https://viu.com",
        "Referer": "https://viu.com/",
    })
    _AREA_ID = {
        'HK': 1,
        'SG': 2,
        'TH': 4,
        'PH': 5,
    }
    _LANGUAGE_FLAG = {
        1: 'zh-hk',
        2: 'zh-cn',
        3: 'en-us',
    }
    cat_map = {
        "kdrama": "Korean Dramas",
        "kvariety": "Korean Variety",
        "asiandrama": "Asian Dramas",
        "thdrama": "Thai Dramas",
        "cdrama": "Chinese Dramas",
        "cvariety": "Chinese Variety"
    }
    if region.lower() in ["hk","sg", "th", "ph"]:
        url = 'https://api-gateway-global.viu.com/api/mobile'
        posts = requests.get(
            url=url,
            headers={
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'x-forwarded-for': '193.56.255.18'  #  bypass SG ip restriction
            },
            params={
                "platform_flag_label": "web",
                "area_id": _AREA_ID.get(region.upper()),
                "language_flag_id": "3",    # keep lang to en
                "platformFlagLabel": "web",
                "areaId": _AREA_ID.get(region.upper()),
                "languageFlagId": "3",      # keep lang to en
                "countryCode": region.upper(),
                "r": "/category/series",
                "length": "16",
                "offset": "0",
                "category_id": "13"
            }
        )
        posts = posts.json()['data']['series']
    else:
        posts = []
    
    if region.lower() == "sg":
        items = list(map(parse, posts))
        if category != "all":
            items = [x for x in items if x and cat_map.get(category.lower(), '') in x['cat']]
            for item in items:
                item.pop('cat')
    else:
        items = []
    return {
        'title': 'VIU New Titles',
        'link': 'https://www.viu.com',
        'description': 'New Titles on VIU',
        'author': 'pandamoon21',
        'items': items
    }