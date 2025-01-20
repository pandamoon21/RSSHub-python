import requests
from rsshub.utils import DEFAULT_HEADERS

audio_map = {
    "00": "2.0 Audio",
    "01": "5.1 Audio"
}

hdr_map = {
    "00": "SDR",
    "01": "HDR"
}

def to_hms(s):
    s = int(s)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return "{:02}:{:02}:{:02}".format(int(h), int(m), int(s))

def parse(post):
    item = {}
    program_id = post.get('code')
    title = post.get('title')
    year = post.get('releaseDate')[:4]
    if year:
        title += f" - {year}"
    item['title'] = title
    imgurl = f"{post.get('imageUrl')}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{program_id}"
    # movies details
    label = post['label']
    drm = "DRM" if label.get('isDrm', False) else ""
    uhd = "UHD" if label.get('isUhd4k', False) else "HD"
    ppv = "PPV" if label.get('isPPV', False) else ""
    rating = "Rating: 18+" if label.get('isGrade18') else "Rating: All"
    subtitle = "CC" if label.get('isSubtitle', False) else ""
    playtime = to_hms(post.get('totalPlayTime', 0))
    details = [
        drm, uhd, ppv, subtitle, rating
    ]
    details = [x for x in details if x]
    item['description'] = "{}<br>{}<br>{}<br>{}".format(
        'Info : ' + ', '.join(details),
        f'Duration: {playtime}',
        f"<a href='{link}'>Link series</a>",
        # post['post']['synopsis'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    rls_date = str(post.get('releaseDate', 0))
    if rls_date != "0":
        item['pubDate'] = "{}-{}-{} 00:00:01".format(
            rls_date[:4], rls_date[4:-8], rls_date[6:-6]
        )
    return item


def ctx():
    DEFAULT_HEADERS.update({'Referer': 'https://atv.tving.com/'})
    apikey = "1e7952d0917d6aab1f0293a063697610"
    # url = 'https://api.tving.com/v2/operator/highlights'
    url = "https://gw.tving.com/bff/tv/v3/more/curation/CR0186"
    # https://gw.tving.com/bff/tv/v3/more/curation/CR0186?screenCode=CSSD1300&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900&apiKey=1e7952d0917d6aab1f0293a063697610&pocType=APP_X_TVING_0.0.0&region=
    posts = requests.get(
        url=url,
        params={
            "screenCode": "CSSD1300",
            "networkCode": "CSND0900",
            "osCode": "CSOD0900",
            "teleCode": "CSCD0900",
            "apiKey": apikey,
            "pocType": "APP_X_TVING_0.0.0",
            "positionKey": "SMTV_MV_4K"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['data']['bands'][0]['items']
    items = list(map(parse, posts))
    return {
        'title': 'TVING New Movies 4K UHD',
        'link': "https://www.tving.com/movie",
        'description': 'New 4K UHD Movies on TVING',
        'author': 'pandamoon21',
        'items': items
    }