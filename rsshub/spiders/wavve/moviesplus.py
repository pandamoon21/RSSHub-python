import re
import requests
from rsshub.utils import DEFAULT_HEADERS

def to_hms(s):
    s = int(s)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return "{:02}:{:02}:{:02}".format(int(h), int(m), int(s))
            
def parse(post):
    item = {}
    posturl  = next(x['url'] for x in post['event_list'] if x['type'] == 'on-navigation')
    movieid = re.search(r"(?<=movieid=)(.*)", posturl).group(1)
    data = requests.get(
        url=f'https://apis.wavve.com/fz/movie/contents/{movieid}',
        headers={
            "apikey": "E5F3E0D30947AA5440556471321BB6D9",
            "credential": "none",
            "device": "pc",
            "drm": "wm",
            "partner": "pooq",
            "pooqzone": "none",
            "region": "kor",
            "targetage": "all"
        }
    ).json()
    title = data.get("origintitle") or post['alt']
    try:
        date = data["releasedate"]
    except KeyError:
        date = data["originalreleasedate"]
    item['title'] = f"{title} - {date[:4]}"
    imgurl = f"https://{post['thumbnail']}"
    price = data.get('price')
    age = data.get('targetage')
    subtitle = data.get('issubtitle')
    audio = data.get('ismultiaudiotrack')
    duration = to_hms(data['playtime'])
    link = f"https://www.wavve.com{posturl}"
    item['description'] = "{}<br>{}<br>{}".format(
        "Title: {} | Duration: {} | Price: {}₩ | Age: {} | Subs: {} | MultiAudio: {}".format(
            post['alt'], duration, price, age, subtitle, audio
        ),
        f"<a href='{link}'>Link series</a>",
        # data['synopsis'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    item['pubDate'] = "{}-{}-{} 18:00:00".format(
        date[:4], date[5:7], date[8:10]
    )
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https:/wavve.com'})
    url = 'http://apis.wavve.com/cf/movie/contents'
    posts = requests.get(
        url=url,
        params={
            "price": "all",
            "mtype": "ppv",
            "orderby": "paid",
            "contenttype": "movie",
            "genre": "all",
            "WeekDay": "all",
            "uitype": "MN184",
            "uiparent": "GN18-MN184",
            "uirank": "9",
            "broadcastid": "119391",
            "offset": "0",
            "limit": "20",
            "uicode": "MN184"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['cell_toplist']['celllist']
    items = list(map(parse, posts))
    return {
        'title': 'Wavve New Movies Plus',
        'link': 'https://wavve.com',
        'description': 'Wavve New Movies Plus',
        'author': 'pandamoon21',
        'items': items
    }