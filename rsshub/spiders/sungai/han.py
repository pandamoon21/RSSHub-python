import base64
import feedparser
import re
import time

cat_map = {
    "音乐": "Music",
    "电影": "Movie",
    "电视剧": "TV Series",
    "综艺": "Variety Show",
    "动漫": "Cartoon"
}

def parse(post):
    item = {}
    judul = post["title"]
    cat = re.search(r"(?<=\[)(\w+?)(?=\])", judul).group(1)
    judul = judul.replace(cat, cat_map.get(cat, cat))
    judul = judul.replace("HHWEB", "HHWEB ").replace("]", "] ").strip()
    item['title'] = judul
    item['description'] = judul
    item['link'] = post["link"]
    item['author'] = post["author_detail"]["name"]
    item['pubDate'] = time.strftime('%Y-%m-%d %H:%M:%S', post['published_parsed'])
    return item


def ctx():
    sungai = "aHR0cHM6Ly9oaGFuY2x1Yi50b3AvdG9ycmVudHJzcy5waHA/cGFzc2tleT17a2V5fSZyb3dzPTEwJmljYXQ9MSZpc2l6ZT0xJml1cGxkZXI9MQ=="
    satu = "NDU4ODliZTAyZjcwZTlmMA=="
    dua = "NmVhNGE3ZDJiOTBmZGQ2OA=="
    url = base64.b64decode(sungai).decode()
    url = url.format(key=f"{base64.b64decode(satu).decode()}{base64.b64decode(dua).decode()}")
    feed = feedparser.parse(url)
    items = list(map(parse, feed.entries))
    return {
        'title': 'Sungai WEB',
        'link': "https://google.com",
        'description': 'New Sungai WEB',
        'author': 'thomas',
        'items': items
    }