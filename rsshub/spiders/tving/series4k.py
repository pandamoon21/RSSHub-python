import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    program_id = post['code']
    title = post['title']
    channel = post.get('channelName')
    if channel:
        title += f" - {channel}"
    item['title'] = title
    imgurl = f"{post['thumbnailImageUrl']}/dims/resize/F_webp,720"
    path2 = post.get('imageUrl')
    if path2:
        imgurl2 = f"{path2}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{program_id}"
    season = post.get('seasonCount', 1)
    uhd = "UHD" if post['label'].get('isUhd4k', False) else "HD"
    cc = "CC" if post['label'].get('isExplainSubtitle', False) else ""
    drm = "DRM" if post['label'].get('isDrm', False) else ""
    only = "TVING Only" if post['label'].get('isOnly', False) else ""
    infos = [x for x in [uhd, cc, drm, only] if x]
    info = "Season: {}<br>Info: {}".format(season, ", ".join(infos))
    item['description'] = "{}<br>{}<br>{}<br>{}".format(
        f"<a href='{link}'>Link series</a>",
        info,
        # post['synopsis'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        f"<img referrerpolicy='no-referrer' src='{imgurl2}'>" if path2 else ""
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    """
    rls_date = str(post.get('display_start_date', 0))[:-6]
    if rls_date != "0":
        # 20230710
        item['pubDate'] = "{}-{}-{} 00:00:01".format(
            rls_date[:4], rls_date[4:6], rls_date[-2:]
        )
    """
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https://atv.tving.com/'})
    apikey = "1e7952d0917d6aab1f0293a063697610"
    url = 'https://gw.tving.com/bff/tv/v3/more/curation/CR0185'
    posts = requests.get(
        url=url,
        params={
            "screenCode": "CSSD1300",
            "networkCode": "CSND0900",
            "osCode": "CSOD0900",
            "teleCode": "CSCD0900",
            "apiKey": apikey,
            "pocType": "APP_X_TVING_0.0.0",
            "region": ""
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['data']['bands'][0]['items']
    items = list(map(parse, posts))
    return {
        'title': 'TVING New Series Drama 4K UHD',
        'link': "https://www.tving.com/contents/episodes",
        'description': 'New Series Drama 4K UHD on TVING',
        'author': 'pandamoon21',
        'items': items
    }