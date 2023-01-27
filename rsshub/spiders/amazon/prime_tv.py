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
    withprime = "Yes" if post.get("withPrimeSign", False) else "No"
    link = f"https://primevideo.com/region/eu/detail/{asin}"
    item['description'] = "Info:<br>{}<br>{}<br>{}<br>{}<br>{}".format(
        f"ASIN: {asin} - TitleID: {titleID} - Prime: {withprime}",
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
    queryToken = "eyJ0eXBlIjoicXVlcnkiLCJuYXYiOnRydWUsInBpIjoiZGVmYXVsdCIsInNlYyI6ImNlbnRlciIsInN0eXBlIjoic2VhcmNoIiw"\
                 "icXJ5IjoicF9uX2VudGl0eV90eXBlPVRWIFNob3cmaW5kZXg9ZXUtYW1hem9uLXZpZGVvLW90aGVyJmFkdWx0LXByb2R1Y3Q9MC"\
                 "ZicT0oYW5kIGFtYXpvbl92aWRlb19zdGFydF9kYXRlOicxODB4LTB5JyAoYW5kIHB1YmxpY19yZWxlYXNlX2RhdGU6JzM2NXgtM"\
                 "HgnIChub3Qgc3R1ZGlvOidBbWF6b24gU3R1ZGlvcycpKSkmcHZfb2ZmZXJzPUlEOklEOnN2b2Q6cHJpbWU6dm9kOi0xNjc0ODI1"\
                 "MDAwOjE2NzQ4MjUwMDAtJnNlYXJjaC1hbGlhcz1pbnN0YW50LXZpZGVvJnFzLWF2X3JlcXVlc3RfdHlwZT00JnFzLWlzLXByaW1"\
                 "lLWN1c3RvbWVyPTIiLCJydCI6IkJESGRDd3NtciIsInR4dCI6IkxhdGVzdCBUViIsIm9mZnNldCI6MCwibnBzaSI6MCwib3JlcS"\
                 "I6ImQwODZlMjU2LTlkNGUtNGJmYy05ZDU1LTc3ZjJlMzc0MmFlNzoxNjc0ODI1NDYyMDAwIiwic3RyaWQiOiIxOjExS1VWQ0tSV"\
                 "Fc4RTYyIyNNWlFXR1pMVU1WU0VHWUxTTjUyWEdaTE0iLCJvcmVxayI6ImpzRGowUWwwenJXQllEVHlIcThQbkRxbUc3ZnJKaTM1"\
                 "cnh6RXpERXppckk9Iiwib3JlcWt2IjoxfQ=="
    kue = requests.get("https://pastebin.com/raw/AK5QftEx").text
    posts = requests.get(
        url=url,
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"\
                          "Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.61",
            "viewport-width": "682",
            "x-amzn-client-ttl-seconds": "15",
            "x-amzn-requestid": "F76HAQD94H9EP6WFQ453",
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
            "totalItems": "75",
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
        'title': 'Primevideo Latest TV',
        'link': 'https://primevideo.com',
        'description': 'Latest TV on Primevideo',
        'author': 'pandamoon21',
        'items': items
    }