import re
import requests
import math
from datetime import datetime
from urllib.parse import unquote

from rsshub.utils import DEFAULT_HEADERS

headers = {
    "User-Agent": "OMS(compatible;ServiceType/GTVM;DeviceType/Android;DeviceModel/SM-G950F;OSType/Android;OSVersion/9.0;AppVersion/1.0.1)",
    "X-Forwarded-For": "0.0.0.0/0\" \"."
}

def convert_size(size, tipe=None):
    if size == 0:
        return "0 B"
    if tipe and tipe != "B":
        if tipe == "KB":
            size = int(size) * (2 ** 10)
        elif tipe == "MB":
            size = int(size) * (2 ** 20)
        elif tipe == "GB":
            size = int(size) * (2 ** 30)
        elif tipe == "TB":
            size = int(size) * (2 ** 40)
        elif tipe == "PB":
            size = int(size) * (2 ** 50)
        elif tipe == "EB":
            size = int(size) * (2 ** 60)
        elif tipe == "ZB":
            size = int(size) * (2 ** 70)
        elif tipe == "YB":
            size = int(size) * (2 ** 80)
    else:
        pass
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s:>6.2f} {size_name[i]}"

def get_vod_detail(contentid, menuid):
    res = requests.post(
        url="https://menu.megatvdnp.co.kr:2443/app6/api/gtvm_vod_detail",
        params={
            "istest": "0",
            "buy_list_yn": "N",
            "prdcdc_yn": "N",
            "series_id": "",
            "content_id": contentid,
            "menu_id": menuid
        },
        headers=headers,
        data=""
    )
    data = res.json()
    data['data']['share_url'] = f"https://www.seezntv.com/vodDetail?content_id={contentid}"
    return data

def parse(post):
    item = {}
    judul = unquote(post["title"]).replace("+"," ")
    imgurl = post['image_url']
    imgurl2 = post.get('still_cut_image', '')
    link = post['next_url']
    try:
        contentid = re.search(r"content_id=(-\d+|\d+)", link).group(1)
    except Exception:
        return item
    vod_detail = get_vod_detail(contentid, post['menu_id'])['data']
    year = vod_detail['product_year']
    link_seezn = vod_detail['share_url']
    size = [convert_size(int(x.split("=")[1])) for x in vod_detail["size"].split("|")]
    runtime = vod_detail['runtime'].replace("분", " Minutes").replace("시간", " Hour")
    item['description'] = "{} - {}<br>{}<br>{}<br>{}<br>{}".format(
        f"<a href='{link_seezn}'>Link Seezn</a>",
        f"<a href='{link}'>Link Ori</a>",
        f"Size: {', '.join(size)} | 5.1 Channel: {vod_detail['ch51_yn']} | Runtime: {runtime}",
        f"Story: {unquote(vod_detail['story']).replace('+', ' ')}",
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        f"<img referrerpolicy='no-referrer' src='{imgurl2}'>",
    )
    item['title'] = f"{judul} ({year}) - Rating {post.get('rating', '0')}"
    item['link'] = link_seezn
    try:
        rls_date = str(re.search(r"_nails/(\d+)/", imgurl).group(1))     # 20221220
        item['pubDate'] = "{}-{}-{} 01:00:00".format(
            rls_date[:4], rls_date[4:6], rls_date[-2:]
        )
    except Exception:
        pass
    return item


def ctx(menuid='', orderby=''):
    """
    orderby - regdate, hot, title

    menuid
    latest movie (kor + non kor) = 58533
    latest kor movie = 59182
    """
    url = 'https://menu.megatvdnp.co.kr:2443/app6/api/gtvm_vod_list'
    posts = requests.get(
        url=url,
        params={
            "menu_id": menuid,
            "count": 15,
            "page": "1",
            "orderby": orderby,
            "istest": "0",
            "adult_yn": "N"
        },
        headers=headers
    )
    posts = posts.json()['data']['list'][0]['list_contents']
    items = list(map(parse, posts))
    return {
        'title': 'GenieTV New Contents',
        'link': 'http://menu.megatvdnp.co.kr:38086',
        'description': 'New Contents on GenieTV',
        'author': 'pandamoon21',
        'items': items
    }