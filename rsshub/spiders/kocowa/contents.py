import requests
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    if post['detail_type'] == "season":
        judul = post['meta']['title']['en']
        year = post['meta']['year']
        season = f"{post['meta']['season_number']:02}"
        country = post['meta']['country']
        judul_fix = f"{judul} S{season} - {year}"
        prefix = "season"
    elif post['detail_type'] == "episode":
        judul = post['meta']['parent_title']['en']
        eps = str(post['meta']['episode_number']).zfill(3)
        country = "S.Korea"
        judul_fix = f"{judul} E{eps}"
        prefix = "media"
    provider = post['meta']['provider']
    rating = post['meta']['rating_info']
    if len(post['meta']['tags']) > 0:
        tags = ", ".join(post['meta']['tags'])
    else:
        tags = ", ".join(post['meta']['genres'])
    timestamp_ms = post['meta']['onair_date']
    onair_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    info = f"Air Date: {onair_date} - Country: {country} - Provider: {provider} - Rating: {rating}"
    item['title'] = judul_fix
    imgurl_pt = post['meta']['poster'].get('portrait')
    imgurl_ls = post['meta']['poster'].get('landscape')
    imgurl_lstv = post['meta']['poster'].get('landscape_tv')
    link = f"https://www.kocowa.com/en_us/{prefix}/{post['id']}"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}<br>{e}".format(
        a=f"<a href='{link}'>Link contents</a>",
        b=info,
        c=f"<img referrerpolicy='no-referrer' src='{imgurl_lstv}'>",
        d=f"<img referrerpolicy='no-referrer' src='{imgurl_pt}'>",
        e=f"<img referrerpolicy='no-referrer' src='{imgurl_ls}'>",
        # f=f"{post['meta']['summary']['en']}<br>Tags: {tags}"
    )
    item['link'] = link
    try:
        item['author'] = post['meta'].get('writers', [])[0]
    except IndexError:
        pass
    rls_date = post.get('start_date')
    if rls_date:
        item['pubDate'] = "{}-{}-{} {}:{}:{}".format(
                rls_date[:4], rls_date[5:-12], rls_date[8:-9],
                rls_date[11:-6], rls_date[14:-3], rls_date[-2:]
            )
    return item


def ctx(catalogId=''):
    DEFAULT_HEADERS.update({
        "Origin": "https://www.kocowa.com",
        "Referer": "https://www.kocowa.com/",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "authorization": "anonymous",
        "X-Forwarded-For": "148.72.168.119" # US IP
    })
    url = 'https://prod-fms.kocowa.com/api/v01/fe/menu/get'
    posts = requests.get(
        url=url,
        params={
            "id": catalogId,
            "limit": "36"   # default 36
        },
        headers=DEFAULT_HEADERS
    )
    posts_ = posts.json()['object']['collections']
    posts = next(x['contents']['objects'] for x in posts_ if x['type'] == 'media')
    posts_fix = [x for x in posts if x['type'] == 'media']
    items = list(map(parse, posts_fix))
    return {
        'title': 'Kocowa New Contents',
        'link': 'https://www.kocowa.com/',
        'description': 'New Contents on Kocowa',
        'author': 'pandamoon21',
        'items': items
    }