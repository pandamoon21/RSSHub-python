"""KlikFilm new-movies spider.

Talks to the app API at api.klikfilm.id/v32; request details are kept in the
repo-external reverse-engineering notes.
"""
import base64
import hashlib
import time

import requests

API_BASE = "https://api.klikfilm.id/v32"

# Global params every klikfilm API call carries.
DEFAULT_PARAMS = {
    "cc": "ID",
    "sf": "KFILM",
    "ch": "AND",
    "tel": "DEF",
}

REQUEST_TIMEOUT = 15

_K0 = base64.b64decode(b"a2luZXRpY2FfXw==")
_K1 = base64.b64decode(b"X19zdHVkaW9z")
_K2 = base64.b64decode(b"Xw==")
_K3 = base64.b64decode(b"dA==")


def _q(params, timestamp):
    """Build the request checksum for a param set."""
    merged = dict(params)
    merged[_K3.decode()] = timestamp
    sep = _K2.decode()
    body = "".join(
        f"{sep}{k}{sep}{merged[k]}{sep}" for k in sorted(merged)
    )
    canonical = _K0.decode() + body + _K1.decode()
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def _req(extra=None):
    params = dict(DEFAULT_PARAMS)
    if extra:
        params.update(extra)
    ts = str(int(time.time() * 1000))
    key = _K3.decode()
    params[key] = ts
    params["sig"] = _q({k: v for k, v in params.items() if k != key}, ts)
    return params


def parse(post):
    thumb = post.get("thumbnail") or {}
    poster = thumb.get("380x543") or thumb.get("320x180") or thumb.get("120x90") or ""
    genre = ", ".join(g.get("title", "") for g in post.get("genre") or [])
    category = (post.get("category") or {}).get("title", "")
    subcategory = (post.get("subcategory") or {}).get("title", "")

    label = post.get("label")
    title = post.get("title", "")
    if label:
        title = f"[{label}] {title}"

    description_parts = []
    meta = " | ".join(p for p in (genre, category, subcategory, post.get("access")) if p)
    if meta:
        description_parts.append(meta)
    if poster:
        description_parts.append(f"<img referrerpolicy='no-referrer' src='{poster}'>")

    return {
        "title": title,
        "description": "<br>".join(description_parts),
        "link": f"https://klikfilm.com/video/{post.get('id')}",
    }


def ctx(section=''):
    """section - a highlights category id, e.g. 33 (Premiere), 107 (KlikFilm Origin)."""
    try:
        res = requests.post(
            f"{API_BASE}/video.highlights-list",
            data=_req({"cat": section, "offset": "0"}),
            timeout=REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        payload = res.json()
        if payload.get("status") != "success":
            err = (payload.get("error") or {}).get("desc", "unknown error")
            print(f"[klikfilm] API error for section={section!r}: {err}")
            posts = []
        else:
            posts = (payload.get("data") or {}).get("content", [])
    except Exception as e:
        print(f"[klikfilm] request failed for section={section!r}: {e}")
        posts = []

    items = [x for x in map(parse, posts) if x]

    return {
        'title': 'KlikFilm New Movies',
        'link': 'https://klikfilm.com',
        'description': 'New Movies on KlikFilm',
        'author': 'pandamoon21',
        'items': items
    }
