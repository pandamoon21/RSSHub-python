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

def parse(post):
    item = {}
    item['title'] = post['vod_name']['ko']
    imgurl = f"https://image.tving.com{post['movie']['image'][1]['url']}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{post['vod_code']}"
    movie_ = post['movie']
    # movies details
    ori_cp = movie_['original_cp']
    duration = movie_.get('duration') or 0
    drm = "DRM" if movie_.get('drm_yn') == "Y" else ""
    cine = "CINE" if movie_.get('cine_same_yn') == "Y" else ""
    first_open = "FIRST" if movie_.get('first_open_yn') == "Y" else ""
    direct = "DIRECT Ver" if movie_.get('direct_ver_yn') == "Y" else ""
    dubver = "DUB Ver" if movie_.get('dub_ver_yn') == "Y" else ""
    subver = "HC Ver" if movie_.get('subtitle_ver_yn') == "Y" else ""
    uneditver = "Uncensored Ver" if movie_.get('unedit_ver_yn') == "Y" else ""
    specialver = "Special Ver" if movie_.get('special_ver_yn') == "Y" else ""
    event = "EVENT" if movie_.get('event_yn') == "Y" else ""
    original = "TVING Original" if movie_.get('tving_original_yn') == "Y" else ""
    exclusive = "TVING Exclusive" if movie_.get('tving_exclusive_yn') == "Y" else ""
    drm4k = "DRM 4K" if movie_.get('drm_4k_yn') == "Y" else ""
    audio_type = audio_map.get(movie_.get('audio_type', "00")) or movie_.get('audio_type')
    hdr_type = hdr_map.get(movie_.get('hdr_type', "00")) or movie_.get('hdr_type')
    freeyn = "FREE" if movie_.get('free_yn') == "Y" else "PAID"
    ko_cc = "Korean CC" if movie_.get('ko_cc_yn') == "Y" else ""
    uhd = "UHD" if movie_.get('uhd_4k_yn') == "Y" else ""
    details = [
        ori_cp, drm, cine, first_open, direct, dubver, subver, event, original, exclusive,
        drm4k, audio_type, hdr_type, freeyn, ko_cc, uhd, uneditver, specialver
    ]
    details = [x for x in details if x]
    item['description'] = "{}<br>{}<br>{}".format(
        'Info : ' + ', '.join(details),
        # post['movie']['story']['ko'],
        f"<a href='{link}'>Link movie</a>",
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
    )
    item['link'] = link
    item['author'] = next((x for x in post['movie'].get('director', [])), "pandamoon21")
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