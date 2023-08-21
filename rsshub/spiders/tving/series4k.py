import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    program_id = post['content_code']
    title = post['content']['program']['name']['ko']
    year = post['content']['program'].get('product_year', '')
    if year:
        title += f" - {year}"
    item['title'] = title
    path = post['content']['program']['image'][0]['url']
    try:
        path2 = post['content']['episode']['image'][0]['url']
    except IndexError:
        path2 = ""
    imgurl = f"https://image.tving.com{path}/dims/resize/F_webp,720"
    if path2:
        imgurl2 = f"https://image.tving.com{path2}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{program_id}"
    item['description'] = "{}<br>{}<br>{}".format(
        f"<a href='{link}'>Link series</a>",
        # post['content']['program']['synopsis']['ko'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        f"<img referrerpolicy='no-referrer' src='{imgurl2}'>" if path2 else ""
    )
    item['link'] = link
    drc = post['content']['program'].get('director')
    if drc:
        item['author'] = ", ".join(drc) if len(drc) > 1 else drc[0]
    else:
        item['author'] = "pandamoon21"
    rls_date = str(post.get('display_start_date', 0))[:-6]
    if rls_date != "0":
        # 20230710
        item['pubDate'] = "{}-{}-{} 00:00:01".format(
            rls_date[:4], rls_date[4:6], rls_date[-2:]
        )
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https://atv.tving.com/'})
    apikey = "1e7952d0917d6aab1f0293a063697610"
    url = 'https://api.tving.com/v2/operator/highlights'
    posts = requests.get(
        url=url,
        params={
            "screenCode": "CSSD1300",
            "networkCode": "CSND0900",
            "osCode": "CSOD0900",
            "teleCode": "CSCD0900",
            "apiKey": apikey,
            "pocType": "APP_X_TVING_0.0.0",
            "positionKey": "SMTV_PROG_4K"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['body']['result']
    items = list(map(parse, posts))
    return {
        'title': 'TVING New Series Drama 4K UHD',
        'link': "https://www.tving.com/contents/episodes",
        'description': 'New Series Drama 4K UHD on TVING',
        'author': 'pandamoon21',
        'items': items
    }