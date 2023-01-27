import re
import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    judul = post["heading"]
    subjudul = post.get("subHeading")
    if subjudul:
        if not subjudul == "":
            judul += f" - {subjudul.replace('Season ', 'S0')}"
    tahun = post.get("releaseYear")
    if tahun:
        judul += f" ({tahun})"
    item['title'] = judul
    imgurl = post["imageSrc"].replace("_UR1920,1080_UX400_UY225_", "_UR1920,1080_UX720_UY480_")
    titleID = post["titleID"]   # amzn1.dv blablabla
    asin = re.search(r"detail/(.+)/", post["href"]).group(1)
    try:
        rating = post["maturityRating"]["rating"]
    except KeyError:
        rating = "0"
    imdb = post.get("imdbRating", "0")
    sinopsis = post["synopsis"]
    captions = post.get("captions", "No")
    runtime = post.get("runtime", "0")
    withprime = "Yes" if post.get("withPrimeSign", False) else "No"
    link = f"https://primevideo.com/region/eu/detail/{asin}"
    item['description'] = "Info:<br>{}<br>{}<br>{}<br>{}<br>{}".format(
        f"ASIN: {asin} <br>TitleID: {titleID} <br>With Prime: {withprime} <br>Runtime: {runtime}",
        f"Cations: {captions} - Rating: {rating} - IMDB rating: {imdb}",
        f"<a href='{link}'>Link contents</a>",
        sinopsis,
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    if not tahun:
        tahun = datetime.fromtimestamp(int(time.time())).strftime('%Y')
    item['pubDate'] = f"{tahun}-01-01 01:00:00"
    return item


def ctx():
    DEFAULT_HEADERS.update({
        "Origin": "https://primevideo.com",
        "Referer": "https://primevideo.com/",
    })
    url = 'https://www.primevideo.com/region/eu/api/searchDefault'
    queryToken = ("eyJ0eXBlIjoicXVlcnkiLCJuYXYiOnRydWUsInBpIjoiZGVmYXVsdCIsInNlYyI6ImNlbnRlciIsInN0eXBlIjoic2VhcmNoIi"
                  "wicXJ5IjoicF9uX2VudGl0eV90eXBlPU1vdmllJmluZGV4PWV1LWFtYXpvbi12aWRlby1vdGhlciZhZHVsdC1wcm9kdWN0PTAm"
                  "YnE9KGFuZCAoYW5kIGFtYXpvbl92aWRlb19zdGFydF9kYXRlOic2MHgtMHknIChhbmQgcHVibGljX3JlbGVhc2VfZGF0ZTonMz"
                  "Y1eC0weCcpIChub3QgdGl0bGU6J1xcXCJ0cmFpbGVyXFxcIicpKSAobm90IGF2X2tpZF9pbl90ZXJyaXRvcnk6J0lEJykpJnB2"
                  "X29mZmVycz1JRDpJRDpzdm9kOnByaW1lOnZvZDotMTY3NDgzMjIwMDoxNjc0ODMyMjAwLSZzZWFyY2gtYWxpYXM9aW5zdGFudC"
                  "12aWRlbyZxcy1hdl9yZXF1ZXN0X3R5cGU9NCZxcy1pcy1wcmltZS1jdXN0b21lcj0yIiwicnQiOiJ2Uko2QklzbXIiLCJ0eHQi"
                  "OiJMYXRlc3QgbW92aWVzIiwib2Zmc2V0IjowLCJucHNpIjowLCJvcmVxIjoiNDRhODcxMGMtZWUzNS00YjM5LWFjZjctY2I1Mj"
                  "U5YzcwZjlhOjE2NzQ4MzI0NDYwMDAiLCJzdHJpZCI6IjE6MTNQQjA1Nk1KMzJJNCMjTVpRV0daTFVNVlNFR1lMU041MlhHWkxN"
                  "Iiwib3JlcWsiOiJqc0RqMFFsMHpyV0JZRFR5SHE4UG5EcW1HN2ZySmkzNXJ4ekV6REV6aXJJPSIsIm9yZXFrdiI6MX0=")
    kue = requests.get("https://pastebin.com/raw/AK5QftEx").text
    posts = requests.get(
        url=url,
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"\
                          "Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.61",
            "viewport-width": "682",
            "x-amzn-client-ttl-seconds": "15",
            "x-amzn-requestid": "CRGQZSNJS5H21PM9F2QB",
            "x-requested-with": "XMLHttpRequest",
            "accept-encoding": "gzip, deflate, br",
            "cookie": kue,  # need this for non supported region, e.g. with US ip
            "device-memory": "8",
            "dnt": "1",
            "downlink": "9.55",
            "dpr": "1",
            "ect": "4g",
            "rtt": "100",
            "sec-ch-device-memory": "8",
            "sec-ch-dpr": "1",
            'X-Forwarded-For': '0.0.0.0/0" ".'
        },
        params={
            "startIndex": "0",
            "queryToken": queryToken,
            "pageId": "default",
            "queryPageType": "browse",
            "isCrow": "1",
            "isElcano": "1",
            "useNodePlayer": "1",
            "totalItems": "50",
            "refMarker": "atv_sr_infinite_scroll",
            "isHover2019": "1",
            "shouldShowPrimeSigns": "1",
            "ie": "UTF8",
            "ref_": "atv_sr_infinite_scroll"
        },
        allow_redirects=True
    )
    titles = posts.json()["items"]
    items = list(map(parse, titles))
    return {
        'title': 'Primevideo Latest Movie',
        'link': 'https://primevideo.com',
        'description': 'Latest Movie on Primevideo',
        'author': 'pandamoon21',
        'items': items
    }