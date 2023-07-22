import base64
import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    item['title'] = post['clip_title']
    status = post.get('status')
    cid = post.get('cid')
    scid = post.get('scid')
    productid = post.get('productid')
    link = f"https://www.viu.com/ott/id/id/all/abc-{cid}"
    image_link = f"http://i.vuclip.com/p?cid={cid}&t=thumb1280x720"
    item['description'] = "{}<br>{}<br>{}<br>{}<br>{}".format(
        f'Status    : {status}',
        f'CID       : {cid}',
        f'SCID      : {scid}',
        f'ProductID : {productid}',
        f"<img referrerpolicy='no-referrer' src='{image_link}'>",
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    rls_date = str(post.get('createtime', 0))
    # 2023-07-21T10:51:21.000Z
    if rls_date != "0":
        item['pubDate'] = "{}-{}-{} {}:{}:{}".format(
            rls_date[:4], rls_date[5:7], rls_date[8:10],
            rls_date[11:13], rls_date[14:16], rls_date[17:19]
        )
    return item


def ctx(limit=''):
    url = 'aHR0cHM6Ly9jbXMtdWktYmZmLnZ1Y2xpcC5jb20vaW5nZXN0aW9uL2dldFNpbXVsY2FzdERhdGE='
    posts = requests.get(
        url=base64.b64decode(url).decode("utf-8"),
        headers=DEFAULT_HEADERS
    )
    posts = [x for x in posts.json() if x.get("cid")]
    limit = int(limit)
    if limit > 0:
        posts = posts[:limit]
    else:
        pass
    items = list(map(parse, posts))
    return {
        'title': 'VIU New Simulcast Title',
        'link': "https://www.viu.com",
        'description': 'New Simulcast Title on VIU',
        'author': 'pandamoon21',
        'items': items
    }