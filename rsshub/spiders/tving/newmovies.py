import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    item['title'] = post['vod_name']['ko']
    imgurl = f"https://image.tving.com{post['movie']['image'][1]['url']}/dims/resize/F_webp,480"
    link = f"https://www.tving.com/contents/{post['vod_code']}"
    item['description'] = "{a}<br>{b}<br>{c}".format(
        a=post['movie']['story']['ko'],
        b=f"<img referrerpolicy='no-referrer' src={imgurl} />",
        c=f"<a href='{link}'>Link movie</a>"
    )
    item['link'] = link
    item['author'] = post['movie']['director'][0]
    rls_date = str(post.get('service_open_date', 0))
    if rls_date != "0":
        item['pubDate'] = "{}-{}-{} {}:{}:{}".format(
            rls_date[:4], rls_date[4:-8], rls_date[6:-6],
            rls_date[8:-4], rls_date[10:-2], rls_date[-2:]
        )
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https://tving.com'})
    apikey = "1e7952d0917d6aab1f0293a063697610"
    url = 'https://api.tving.com/v2/media/movies'
    posts = requests.get(
        url=url,
        params={
            "pageSize": "24",
            "order": "new",
            "free": "all",
            "adult": "all",
            "guest": "all",
            "scope": "all",
            "personal": "N",
            "pageNo": "1",
            "screenCode": "CSSD0100",
            "networkCode": "CSND0900",
            "osCode": "CSOD0900",
            "teleCode": "CSCD0900",
            "apiKey": apikey
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['body']['result']
    items = list(map(parse, posts))
    return {
        'title': 'TVING New Movies',
        'link': "https://www.tving.com/contents/movie",
        'description': 'New Movies on TVING',
        'author': 'pandamoon21',
        'items': items
    }