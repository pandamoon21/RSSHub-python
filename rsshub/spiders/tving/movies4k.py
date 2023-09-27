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

def null_to_none(input_):
    if input_ in ["null", 0, "0"]:
        return None
    else:
        return input_

def parse(post):
    item = {}
    program_id = (
        post.get('content_code') or
        post["content"].get("vod_code")
    )
    title = null_to_none(
        post['content']['vod_name']['en'] or
        post['content']['vod_name']['ko']
    )
    year = (
        null_to_none(str(post["content"]["movie"]["release_date"])[:4]) or
        post['content']['movie'].get('product_year', '')
    )
    if year:
        title += f" - {year}"
    item['title'] = title
    movie_ = post['content']['movie']
    path = next((x["url"] for x in movie_['image'] if x["code"] == "CAIM2600"), "")
    if not path:
        path = next((x["url"] for x in movie_['image'] if x["code"] == "CAIM2100"), "")
    if not path:
        path = next((x["url"] for x in movie_['image'] if x["code"] == "CAIM2400"), "")
    if not path:
        path = next((x["url"] for x in movie_['image'] if x["code"] == "CAIM0400"), "")
    if not path:
        path = movie_['image'][0]["url"]
    imgurl = f"https://image.tving.com{path}/dims/resize/F_webp,720"
    link = f"https://www.tving.com/contents/{program_id}"
    # movies details
    ori_cp = movie_['original_cp']
    duration = movie_.get('duration') or 0
    drm = "DRM" if movie_['drm_yn'] == "Y" else ""
    cine = "CINE" if movie_['cine_same_yn'] == "Y" else ""
    first_open = "FIRST" if movie_['first_open_yn'] == "Y" else ""
    direct = "DIRECT Ver" if movie_['direct_ver_yn'] == "Y" else ""
    dubver = "DUB Ver" if movie_['dub_ver_yn'] == "Y" else ""
    subver = "HC Ver" if movie_['subtitle_ver_yn'] == "Y" else ""
    uneditver = "Uncensored Ver" if movie_['unedit_ver_yn'] == "Y" else ""
    specialver = "Special Ver" if movie_['special_ver_yn'] == "Y" else ""
    event = "EVENT" if movie_['event_yn'] == "Y" else ""
    original = "TVING Original" if movie_['tving_original_yn'] == "Y" else ""
    exclusive = "TVING Exclusive" if movie_['tving_exclusive_yn'] == "Y" else ""
    drm4k = "DRM 4K" if movie_['drm_4k_yn'] == "Y" else ""
    audio_type = audio_map.get(movie_.get('audio_type', "00")) or movie_.get('audio_type')
    hdr_type = hdr_map.get(movie_.get('hdr_type', "00")) or movie_.get('hdr_type')
    freeyn = "FREE" if movie_['free_yn'] == "Y" else "PAID"
    ko_cc = "Korean CC" if movie_.get('ko_cc_yn') == "Y" else ""
    uhd = "UHD" if movie_['uhd_4k_yn'] == "Y" else ""
    details = [
        ori_cp, drm, cine, first_open, direct, dubver, subver, event, original, exclusive,
        drm4k, audio_type, hdr_type, freeyn, ko_cc, uhd, uneditver, specialver
    ]
    details = [x for x in details if x]
    item['description'] = "{}<br>{}<br>{}".format(
        'Info : ' + ', '.join(details),
        f"<a href='{link}'>Link series</a>",
        # post['content']['movie']['synopsis']['ko'],
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    drc = post['content']['movie'].get('director')
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
            "positionKey": "SMTV_MV_4K"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['body']['result']
    items = list(map(parse, posts))
    return {
        'title': 'TVING New Movies 4K UHD',
        'link': "https://www.tving.com/movie",
        'description': 'New 4K UHD Movies on TVING',
        'author': 'pandamoon21',
        'items': items
    }