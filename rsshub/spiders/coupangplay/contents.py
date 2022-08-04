import requests
from rsshub.utils import DEFAULT_HEADERS

def get_date(rls_date):
    date = "{}-{}-{} {}:{}:{}".format(
        rls_date[:4], rls_date[5:7], rls_date[8:10],
        rls_date[11:13], rls_date[14:16], rls_date[17:19]
    )
    return date

def parse(post):
    item = {}
    judul = post['title']
    season = post.get('seasons', None)
    if season:
        judul += " S{:02}".format(season)
    year = post['meta'].get('releaseYear', None)
    if year:
        judul += f" {year}"
    judul += f" - {post['as']}"
    item['title'] = "{}".format(judul)
    imgurl = "{}{}".format(
        post['images']['background']['url'],
        "?imwidth=800&imheight=200&imscalingMode=aspectFit"
    )
    link = f"https://www.coupangplay.com/titles/{post['id']}"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}".format(
        a=f"Rating: {post['age_rating']} - {get_date(post['updated_at'])}",
        b=f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        c=post['short_description'],
        d=f"<a href='{link}'>Link contents</a>"
    )
    item['link'] = link
    item['pubDate'] = get_date(str(post['published_at']))
    return item


def ctx(menuid=''):
    DEFAULT_HEADERS.update({
        "Origin": "https://www.coupangplay.com",
        "Referer": "https://www.coupangplay.com/",
    })
    url = 'https://discover.coupangstreaming.com/v2/discover/feed'
    posts = requests.get(
        url=url,
        headers=DEFAULT_HEADERS,
        params={
            "category": "ALL",  # TVSHOW, 
            "platform": "WEBCLIENT",
            "region": "KR",
            "locale": "ko",
            "page": "1",
            "perPage": "10",
            "filterRestrictedContent": "false",
            "preferRecoFeed": "true",
            "preferMultiHeroMixedContentRow": "true"
        }
    )
    # new contents curation only - row_name = 새로 올라온 콘텐츠
    posts = next(x['data'] for x in posts.json()['data'] if x['row_id'] == '1bcb5138-edca-472b-93ab-58ec35e75d16')
    items = list(map(parse, posts))
    return {
        'title': 'CoupangPlay New Contents',
        'link': 'https://www.coupangplay.com/home',
        'description': 'New Contents on CoupangPlay',
        'author': 'pandamoon21',
        'items': items
    }