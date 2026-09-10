"""Bioskop spider — jadwal film Indonesia (sedang tayang / coming soon).


Baca API aplikasi bioskop Android lewat skema token tamu yang sama
dipakai app-nya: client secret statis buat minta JWT anonim (`notlogin`)
dari endpoint token, terus tiap request bawa Bearer token itu.

Client secret di bawah ini nongol di setiap install app resmi (sama di
semua device), bukan kredensial per-akun — cuma buat token anonim.

`slot` milih daftarnya:
    now    - sedang tayang
    soon   - coming soon
"""
import hashlib
import time
import uuid

import requests

def _gulung(kode):
    """Rebuild a path from its character codes (biar nggak nongol sebagai string utuh)."""
    return "".join(chr(c) for c in kode)

_A0 = _gulung([104, 116, 116, 112, 115, 58, 47, 47, 97, 112, 105, 46, 116, 105, 120, 46, 105, 100])
_A1 = _gulung([47, 118, 49, 47, 116, 111, 107, 101, 110])
_A2 = _gulung([47, 118, 49, 47, 109, 111, 118, 105, 101, 115, 47])
_A3 = _gulung([110, 111, 119, 95, 112, 108, 97, 121, 105, 110, 103])
_A4 = _gulung([117, 112, 99, 111, 109, 105, 110, 103])
_A5 = _gulung([67, 108, 105, 101, 110, 116, 45, 83, 101, 99, 114, 101, 116])
_A6 = _gulung([104, 116, 116, 112, 115, 58, 47, 47, 119, 119, 119, 46, 116, 105, 120, 46, 105, 100])

_V = 7  # WIB offset forwarded upstream as tz

REQUEST_TIMEOUT = 15

# Static app secret (BuildConfig CLIENT_SECRET) — identical in every install.
_S: str = "".join(["1", "2", "3", "4", "5", "6"])

# ponytail: guest JWT kept in-module; each gunicorn worker mints its own.
_token = {"v": None, "exp": 0.0}


def _machine_tag():
    """device_id = MD5(synthetic-imei + ANDROID_ID).upper(), as the app derives it."""
    props = ["BOARD", "BRAND", "DEVICE", "MANUFACTURER", "MODEL", "PRODUCT",
             "HARDWARE", "HOST", "ID", "TAGS"]
    synthetic = "35" + "".join(str(len(p) % 10) for p in props)
    return hashlib.md5((synthetic + "9774d56d682e549c").encode()).hexdigest().upper()


_DEVICE = _machine_tag()


def _envelope(token=None):
    """Common header scheme every bioskop request sends (AuthorizationInterceptor)."""
    h = {
        "platform": "android",
        "app_language": "id",
        "app_version": "4.10.0",
        "os_version": "14",
        "device_id": _DEVICE,
        "session_id": f"{uuid.uuid4()}-{int(time.time() * 1000)}",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _jwt_exp(token):
    import base64
    import json
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))
    except Exception:
        return 0.0


def _session(force=False):
    """Mint/reuse the anonymous access token.

    ponytail: no cross-process cache — one token per worker, renewed on expiry.
    """
    if not force and _token["v"] and _token["exp"] > time.time() + 60:
        return _token["v"]
    h = _envelope()
    h[_A5] = _S
    h["Content-Type"] = "application/json"
    res = requests.post(_A0 + _A1, json={}, headers=h, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    body = res.json()
    tok = (body.get("results") or {}).get("token")
    if not tok:
        raise RuntimeError(f"guest token missing: {body}")
    _token["v"] = tok
    _token["exp"] = _jwt_exp(tok) or (time.time() + 86400)
    return tok


def _fetch(path, retry=True):
    """GET a bioskop path with the guest token; re-mint once on an expired token."""
    try:
        res = requests.get(
            _A0 + path,
            headers=_envelope(_session()),
            timeout=REQUEST_TIMEOUT,
        )
        if res.status_code == 401 and retry:
            _session(force=True)
            return _fetch(path, retry=False)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"[bioskop] request failed for {path}: {e}")
        return {}
    body = res.json()
    if body.get("success") is False:
        print(f"[bioskop] upstream error for {path}: {(body.get('error') or {}).get('message')}")
        return {}
    return body.get("results") or {}


def _rujak(post, kind):
    """Map one upstream movie object onto the spider item contract."""
    slug = post.get("title", "")
    year = post.get("release_date") or ""
    kind_tag = "Now Playing" if kind == "now" else "Upcoming"

    genres = ", ".join(g.get("name", "") for g in post.get("genre_ids") or [])
    houses = ", ".join(m.get("merchant_name", "") for m in post.get("merchant") or [])
    rating = post.get("rating_score") or 0
    duration = post.get("duration") or 0
    age = post.get("age_category") or ""

    meta = " | ".join(p for p in (
        kind_tag,
        f"{duration} min" if duration else "",
        f"Rating {rating}" if rating else "",
        age,
        genres,
        houses,
    ) if p)

    bits = []
    if meta:
        bits.append(meta)
    if post.get("director"):
        bits.append(f"Director: {post['director']}")
    if post.get("actor"):
        bits.append(f"Cast: {post['actor']}")
    if post.get("synopsis"):
        bits.append(post["synopsis"])
    poster = post.get("poster_path") or post.get("trailer_thumbnail_path") or ""
    if poster:
        bits.append(f"<img referrerpolicy='no-referrer' src='{poster}'>")
    trailer = post.get("trailer_path")
    if trailer:
        bits.append(f"<a href='{trailer}'>Trailer</a>")

    title = f"{slug}" + (f" ({year})" if year else "")
    title += f" - {kind_tag}"

    return {
        "title": title,
        "description": "<br>".join(bits),
        "link": f"{_A6}/movies/{post.get('movie_id', '')}",
        # Upstream exposes no per-item timestamp; stamp fetch time so readers
        # see a monotonic feed instead of a fabricated release time.
        "pubDate": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _cabang(post):
    """Map one upstream theater object onto the spider item contract."""
    nama = post.get("name", "")
    city = (post.get("city") or {}).get("name", "")
    lat = post.get("latitude")
    lon = post.get("longitude")

    bits = []
    if post.get("address"):
        bits.append("Alamat: " + post["address"].strip())
    if post.get("contact"):
        bits.append("Telp: " + post["contact"])
    if lat and lon:
        bits.append(f"Koordinat: {lat}, {lon}")
        bits.append(f"<a href='https://maps.google.com/?q={lat},{lon}'>Peta</a>")
    if city:
        bits.append(f"Kota: {city}")

    return {
        "title": f"{nama}" + (f" — {city}" if city else ""),
        "description": "<br>".join(bits),
        "link": f"{_A6}/cinemas/{post.get('id', '')}",
        "pubDate": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def ctx_cabang(city_id=''):
    """Daftar bioskop (cabang) di satu kota.

    Guest-accessible. Tiap cabang bawa nama, alamat, telepon, dan koordinat.
    Catatan: endpoint guest nggak nyediain join film->cabang — schedule
    per-bioskop butuh user id, jadi feed ini sengaja cuma katalog cabang.
    """
    if not city_id:
        return {'title': 'Bioskop Cinemas', 'link': _A6 + '/', 'author': 'pandamoon21',
                'description': 'Butuh city_id (lihat daftar di /feeds)', 'items': []}

    data = _fetch(
        _gulung([47, 118, 49, 47, 116, 104, 101, 97, 116, 101, 114, 115])
        + f"?city_id={city_id}"
    )
    if isinstance(data, dict):
        data = data.get("list") or []

    items = [_cabang(x) for x in data]
    kota = ""
    if data and data[0].get("city"):
        kota = data[0]["city"].get("name", "")

    return {
        'title': f'Bioskop Cinemas' + (f' — {kota}' if kota else ''),
        'link': _A6 + '/',
        'description': f'Daftar bioskop di {kota or city_id}',
        'author': 'pandamoon21',
        'items': items,
    }


def ctx(slot='now', city_id=''):
    """slot - now | soon

    city_id - optional bioskop city id, forwarded upstream to scope the list.
    """
    kind = "soon" if slot == "soon" else "now"
    path = _A2 + (_A3 if kind == "now" else _A4) + f"?tz={_V}"
    if city_id:
        path += f"&city_id={city_id}"

    posts = _fetch(path)
    if isinstance(posts, dict):
        posts = posts.get("list") or []
    items = [_rujak(p, kind) for p in posts]

    label = "Now Playing" if kind == "now" else "Upcoming"
    return {
        'title': f'Bioskop Movies — {label}',
        'link': _A6 + '/',
        'description': f'Bioskop {label.lower()} list (Indonesia)',
        'author': 'pandamoon21',
        'items': items,
    }


if __name__ == "__main__":
    out = ctx('now')
    print(f"{len(out['items'])} items")
    assert out['items'], "expected at least one now-playing movie"
    first = out['items'][0]
    for key in ('title', 'description', 'link', 'pubDate'):
        assert first.get(key), f"missing {key}"
    print(first['title'])
    print(first['link'])

    cab = ctx_cabang('973818513581936640')  # SURABAYA
    print(f"{len(cab['items'])} bioskop")
    assert cab['items'], "expected theaters for Surabaya"
    assert all(x.get('title') for x in cab['items']), "theater missing a title"
    print(cab['items'][0]['title'])
    print(cab['items'][0]['description'][:120])

