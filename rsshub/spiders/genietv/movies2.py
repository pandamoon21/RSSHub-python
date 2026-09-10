"""Genie TV (KT) VOD list spider.

Endpoints and hosts verified against the APK research notes
(Research-APK_GenieTV, phone variant com.kt.gtv):
  - VOD list:   POST https://contents.megatvdnp.co.kr/app6/api/gtvm_vod_list
  - VOD detail: POST https://contents.megatvdnp.co.kr/app6/api/gtvm_vod_detail

Both live on SERVER_OMS_CONTENT (base already includes app6/api/); the older
menu.megatvdnp.co.kr:2443 host no longer answers. Seeezen (seezntv.com) is
shut down, so detail links point at the Genie TV web player instead.

Note: these hosts are KT-operated and geo-restricted to Korea; requests from
outside KR will be reset.
"""
import re
from urllib.parse import unquote

import requests

# OMS client identity, as sent by the Genie TV Android app.
headers = {
    "User-Agent": (
        "OMS(compatible;ServiceType/GTVM;DeviceType/Android;"
        "DeviceModel/SM-G950F;OSType/Android;OSVersion/9.0;AppVersion/1.0.1)"
    ),
}

BASE_URL = "https://contents.megatvdnp.co.kr/app6/api"
REQUEST_TIMEOUT = 10

# Public Genie TV web player; used as the human-facing detail link.
WEB_DETAIL = "https://tv.kt.com/gtv/vod/detail?content_id={content_id}"


def get_vod_detail(content_id, menu_id):
    """Fetch VOD detail (OMS). Returns the 'data' object, or None on failure."""
    try:
        res = requests.post(
            url=f"{BASE_URL}/gtvm_vod_detail",
            params={
                "istest": "0",
                "buy_list_yn": "N",
                "prdcdc_yn": "N",
                "series_id": "",
                "content_id": content_id,
                "menu_id": menu_id,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        return res.json().get("data")
    except Exception as e:
        print(f"[genietv] vod_detail failed for {content_id}: {e}")
        return None


def parse(post):
    item = {}
    judul = unquote(post.get("title", "")).replace("+", " ")
    imgurl = post.get("image_url", "")
    imgurl2 = post.get("still_cut_image", "")
    link = post.get("next_url", "")

    m = re.search(r"(?:content_id|series_id)=(-\d+|\d+)", link)
    if not m:
        return item
    content_id = m.group(1)

    web_link = WEB_DETAIL.format(content_id=content_id)
    detail = get_vod_detail(content_id, post.get("menu_id", ""))

    size_txt = ""
    runtime_txt = ""
    year = None
    if detail:
        year = detail.get("product_year")
        if detail.get("size"):
            size_txt = "Size: " + ", ".join(
                _human_size(x) for x in detail["size"].split("|") if x
            )
        if detail.get("runtime"):
            runtime_txt = (
                detail["runtime"].replace("분", " Minutes").replace("시간", " Hour")
            )

    parts = [
        f"<a href='{web_link}'>Genie TV</a>",
        f"<a href='{link}'>Original link</a>",
    ]
    runtime_label = f"Runtime: {runtime_txt}" if runtime_txt else ""
    meta = " | ".join(p for p in (size_txt, runtime_label) if p)
    if meta:
        parts.append(meta)
    if imgurl:
        parts.append(f"<img referrerpolicy='no-referrer' src='{imgurl}'>")
    if imgurl2:
        parts.append(f"<img referrerpolicy='no-referrer' src='{imgurl2}'>")

    item["description"] = "<br>".join(parts)
    item["link"] = web_link
    item["title"] = f"{judul}" + (f" ({year})" if year else "")
    item["title"] += f" - Rating {post.get('rating', '0')}"

    # Release date is embedded in the poster path, e.g. .../thumb_nails/20221220/...
    date_match = re.search(r"_nails/(\d{8})/", imgurl)
    if date_match:
        rls_date = date_match.group(1)
        item["pubDate"] = f"{rls_date[:4]}-{rls_date[4:6]}-{rls_date[6:8]} 01:00:00"
    return item


def _human_size(token):
    """Format an OMS size token like 'SZ=12345678' as a human-readable size."""
    try:
        n = int(token.split("=")[-1])
    except (ValueError, IndexError):
        return token
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def ctx(menuid='', orderby=''):
    """
    orderby - regdate, hot, title

    menuid
    latest movie (kor + non kor) = 58533
    latest kor movie = 59182
    """
    try:
        res = requests.get(
            url=f"{BASE_URL}/gtvm_vod_list",
            params={
                "menu_id": menuid,
                "count": 30,
                "page": "1",
                "orderby": orderby,
                "istest": "0",
                "adult_yn": "N",
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        posts = res.json()["data"]["list"][0]["list_contents"]
    except Exception as e:
        print(f"[genietv] vod_list failed (menu={menuid}, orderby={orderby}): {e}")
        posts = []

    items = [x for x in map(parse, posts) if x]

    return {
        'title': 'GenieTV New Contents',
        'link': 'https://tv.kt.com/gtv/',
        'description': 'New Contents on GenieTV',
        'author': 'pandamoon21',
        'items': items
    }
