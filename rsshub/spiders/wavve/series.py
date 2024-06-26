import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    try:
        title = post['title_list'][0]['text']
    except (KeyError, IndexError):
        title = post.get('alt', 'No Title')
    try:
        epsnum =  post['title_list'][1]['text'].split(
            "회")[0].split("(")[0].zfill(2)
        item['title'] = f"{title} - E{epsnum}"
    except Exception:
        item['title'] = title
    imgurl = f"https://{post['thumbnail']}"
    path = post['event_list'][1]['url']
    link = f"https://www.wavve.com{path}"
    item['link'] = link
    item['description'] = "{}<br>{}".format(
        # post['title_list'][1]['text'],
        f"<a href='{link}'>Link series</a>",
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    """
    try:
        date = post['title_list'][1]['text'].split(" ")[2].split("(")[0]
    except (IndexError, Exception):
        date = post['title_list'][1]['text'].split("(")[0]
    item['pubDate'] = "{}-{}-{} 18:00:00".format(
        date[:4], date[5:7], date[8:10]
    )
    """
    return item


def ctx(order=''):
    DEFAULT_HEADERS.update({'Referer': 'https:/wavve.com'})
    url = 'https://apis.pooq.co.kr/cf/vod/popularcontents'
    posts = requests.get(
        url=url,
        params={
            "WeekDay": "all",
            "adult": "n",
            "broadcastid": "6582",
            "came": "broadcast",
            "contenttype": "vod",
            "genre": "01",
            "limit": "20",
            "offset": "0",
            "orderby": order,
            "page": "1",
            "uiparent": "GN2-VN4",
            "uirank": "3",
            "uitype": "VN4",
            "apikey": "E5F3E0D30947AA5440556471321BB6D9",
            "credential": "none",
            "device": "pc",
            "drm": "wm",
            "partner": "pooq",
            "pooqzone": "none",
            "region": "kor",
            "targetage": "all"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['cell_toplist']['celllist']
    items = list(map(parse, posts))
    return {
        'title': 'Wavve New Series',
        'link': 'https://wavve.com',
        'description': 'Wavve New Series',
        'author': 'pandamoon21',
        'items': items
    }