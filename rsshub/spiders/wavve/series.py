import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    title = post['title_list'][0]['text']
    epsnum =  post['title_list'][1]['text'].split("회")[0].zfill(2)
    item['title'] = f"{title} - E{epsnum}"
    imgurl = f"https://{post['thumbnail']}"
    item['description'] = "{a}<br>{b}".format(
        a=post['title_list'][1]['text'],
        b=f"<img referrerpolicy='no-referrer' src={imgurl}>"
    )
    path = post['event_list'][1]['url']
    item['link'] = f"https://www.wavve.com{path}"
    date = post['title_list'][1]['text'].split(" ")[2]
    item['pubDate'] = "{}-{}-{} 00:00:00".format(
        date[:4], date[5:-6], date[8:-3]
    )
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