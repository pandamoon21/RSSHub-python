import httpx

def parse(post):
    item = {}
    title = post['titles']['original'].replace("시즌", "Season")
    subtitle = post.get('subtitle')
    if subtitle:
        title += f" - {subtitle}"
    item['title'] = f"{title}"
    imgurl = post['media']['large']
    link = f"https://watcha.com/contents/{post['relations'][0]['id']}"
    item['description'] = "{a}<br>{b}<br>{c}".format(
        a=f"<a href='{link}'>Link contents</a>",
        b=title,
        c=f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    return item


def ctx():
    url = 'https://api-mars.watcha.com/api/aio_staffmades/gsm6N0pw3N'
    posts = httpx.get(
        url=url,
        headers={
            'Origin': 'https://watcha.com',
            "Referer": "https://watcha.com",
            # "x-watchaplay-client": "WatchaPlay-WebApp",
            'x-watchaplay-client': 'WatchaPlay-Android',
            # "x-watchaplay-client-device-id": "web-HCnjKRvABgIlu-1HnIEIHJMmMZeN6H",
            'x-watchaplay-client-device-id': 'web-8-ahL1Wi2gumQkYXkZIr4uMKE7gwPD',
            'X-FROGRAMS-MARS-CODEC-FLAG': '3',
            'X-WatchaPlay-Client-HDR-Capabilities': "1",
            'X-WatchaPlay-Client-Audio-Capabilities': '1',
            'X-WatchaPlay-Screen': '3120x1440/3.5/560/xxxhdpi',
            'x-watchaplay-client-language': 'en',
            'X-FROGRAMS-MARS-HDR-CAPABILITIES': '1',
            'X-FROGRAMS-MARS-AUDIO-CAPABILITIES': '1',
            'X-WatchaPlay-Client-Codec-Flag': '3',
            'x-watchaplay-client-region': 'KR', 
            # "x-watchaplay-client-version": "1.0.3",
            'x-watchaplay-client-version': '1.10.39',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; Redmi Note 9 Pro Build/RKQ1.200826.002)/WatchaPlay-Android/1.9.89'
        },
        proxies={
            'http://': 'http://af34eda5-98eb-42e4-9fc5-3ae8957cf66c:Z05Wbhh0w0@seoul.wevpn.com:3128',
            'https://': 'http://af34eda5-98eb-42e4-9fc5-3ae8957cf66c:Z05Wbhh0w0@seoul.wevpn.com:3128'
        },
        verify=False
    )
    posts = posts.json()['result']['contents']['items']
    items = list(map(parse, posts))
    return {
        'title': 'Watcha New Episodes',
        'link': "https://watcha.com/staffmades/gsm6N0pw3N",
        'description': 'Watcha New Episodes',
        'author': 'pandamoon21',
        'items': items
    }