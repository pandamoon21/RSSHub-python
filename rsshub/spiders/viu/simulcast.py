import base64
import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    title = post.get('clip_title')
    if not title:
        return None
    
    item['title'] = title
    status = post.get('status')
    cid = post.get('cid')
    scid = post.get('scid')
    productid = post.get('productid')
    
    # Updated link pattern to use 'video-' prefix which handles redirection better
    link = f"https://www.viu.com/ott/id/id/all/video-{cid}"
    # Use HTTPS for images
    image_link = f"https://i.vuclip.com/p?cid={cid}&t=thumb1280x720"
    
    item['description'] = "{}<br>{}<br>{}<br>{}<br>{}".format(
        f'Status    : {status}',
        f'CID       : {cid}',
        f'SCID      : {scid}',
        f'ProductID : {productid}',
        f"<img referrerpolicy='no-referrer' src='{image_link}'>",
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    
    rls_date = str(post.get('createtime', ''))
    # Expected format: 2023-07-21T10:51:21.000Z
    if len(rls_date) >= 19:
        item['pubDate'] = "{}-{}-{} {}:{}:{}".format(
            rls_date[:4], rls_date[5:7], rls_date[8:10],
            rls_date[11:13], rls_date[14:16], rls_date[17:19]
        )
    return item


def ctx(limit=''):
    url = 'aHR0cHM6Ly9jbXMtdWktYmZmLnZ1Y2xpcC5jb20vaW5nZXN0aW9uL2dldFNpbXVsY2FzdERhdGE='
    try:
        response = requests.get(
            url=base64.b64decode(url).decode("utf-8"),
            headers=DEFAULT_HEADERS,
            timeout=10
        )
        response.raise_for_status()
        posts = response.json()
    except Exception:
        posts = []
    
    # Filter items with cid and de-duplicate by cid
    seen_cids = set()
    valid_posts = []
    for x in posts:
        cid = x.get("cid")
        if cid and cid not in seen_cids:
            valid_posts.append(x)
            seen_cids.add(cid)
            
    try:
        limit = int(limit) if limit else 0
    except ValueError:
        limit = 0
        
    if limit > 0:
        valid_posts = valid_posts[:limit]
        
    items = [parse(post) for post in valid_posts]
    items = [item for item in items if item]
    
    return {
        'title': 'VIU New Simulcast Title',
        'link': "https://www.viu.com",
        'description': 'New Simulcast Title on VIU',
        'author': 'pandamoon21',
        'items': items
    }
