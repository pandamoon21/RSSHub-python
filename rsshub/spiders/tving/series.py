import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    cat2 = post['program'].get(
        'display_category2', post['program'].get('category2_code', [])
    )
    if "PCA042" in cat2:
        return item
    channel = post['channel']['code']
    skip_channel = [
        'C00544',   # ChinaTV
        'C51261',   # CNTV
        'C51405',   # Paramount+
        'C04061',   # Channel J
        'C51259',   # CBS
        'C05901',   # Channel W
        'C45541',   # AsiaN
        'C39241',   # Sony
        'C30442',   # Media Genie
        'C05441',   # Anibox
        'C23442',   # Dlive
        'C44742',   # kt alpha
        'C51551',   # 아몬드컴퍼니
        'C35741',   # iMBC (?)
        'C47841',   # SPO KOREA
        'C52055',   # 채널액션
        'C51451',   # 스튜디오산타
    ]
    if channel in skip_channel:
        return item
    title = post['program']['name']['ko']
    epsnum = post['episode']['frequency']
    item['title'] = f"{title} - E{epsnum:02}"
    path = post['program']['image'][0]['url']
    try:
        path2 = post['episode']['image'][0]['url']
    except IndexError:
        path2 = path
    imgurl = f"https://image.tving.com{path}/dims/resize/F_webp,720"
    imgurl2 = f"https://image.tving.com{path2}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{post['vod_code']}"
    link2 = f"https://www.tving.com/contents/{post['program']['code']}"
    item['description'] = "{}<br>{}<br>{}".format(
        f"<a href='{link}'>Link eps</a> - <a href='{link2}'>Link series</a>",
        # post['episode']['synopsis']['ko'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        f"<img referrerpolicy='no-referrer' src='{imgurl2}'>"
    )
    item['link'] = link
    drc = post['program'].get('director')
    if drc:
        item['author'] = ", ".join(drc) if len(drc) > 1 else drc[0]
    else:
        item['author'] = "pandamoon21"
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
    url = 'https://api.tving.com/v2/media/episodes'
    posts = requests.get(
        url=url,
        params={
            "cacheType": "main",
            "pageSize": "24",
            "order": "broadDate",
            "free": "all",
            "adult": "all",
            "guest": "all",
            "scope": "all",
            "lastFrequency": "y",
            "personal": "N",
            "categoryCode": "PCA",
            "pageNo": "1",
            "screenCode": "CSSD0100",
            "networkCode": "CSND0900",
            "osCode": "CSOD0900",
            "teleCode": "CSCD0900",
            "apiKey": apikey
        },
        headers=DEFAULT_HEADERS.update({
            "X-Forwarded-For": "108.181.52.147" # KR ip
        })
    )
    posts = posts.json()['body']['result']
    items = [x for x in list(map(parse, posts)) if x]
    return {
        'title': 'TVING New Series Drama',
        'link': "https://www.tving.com/contents/episodes",
        'description': 'New Series Drama on TVING',
        'author': 'pandamoon21',
        'items': items
    }