import requests
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    item['title'] = f"{post['content_title']} - Rating {post['content_rating']}"
    imgurl = post['image_url']
    link = f"https://www.seezntv.com/vodDetail?content_id={post['content_id']}&menu_id={post['menu_id']}&series_id="
    item['description'] = "{a}<br>{b}<br>{c}".format(
        a=post['content_subtitle'],
        b=f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        c=f"<a href='{link}'>Link contents</a>"
    )
    item['link'] = link
    rls_date = str(post['content_regdate'])
    item['pubDate'] = "{}-{}-{} {}:{}:{}".format(
        rls_date[:4], rls_date[5:-21], rls_date[8:-18],
        rls_date[11:-15], rls_date[14:-12], rls_date[17:-9]
    )
    return item


def ctx(menuid=''):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    transactionid = timestamp + "000000000000001"
    DEFAULT_HEADERS.update({
        "Origin": "https://seezntv.com",
        "Referer": "https://seezntv.com",
        "Accept": "application/json, text/plain, */*",
        "HTTP_CLIENT_IP": "undefined",
        "X-DEVICE-MODEL": "Microsoft Edge",
        "X-APP-VERSION": "101.0.1210.32",
        "X-OS-TYPE": "Windows",
        "X-OS-VERSION": "NT 10.0",
        "X-DEVICE-TYPE": "PCWEB",
        "timestamp": timestamp,
        "transactionId": transactionid,
        "Content-Type": "application/json; charset=UTF-8"
    })
    url = 'https://api.seezntv.com/svc/cmsMenu/record_gw/api/category/content/v2'
    posts = requests.post(
        url=url,
        json={
            "menu_id": menuid,
            "page_count": 30,
            "page_no": "1",
            "order_type": "0",
            "istest": "0"
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['data']['list_content'][::-1]
    items = list(map(parse, posts))
    return {
        'title': 'Seezn New Contents',
        'link': 'https://www.seezntv.com/category/102',
        'description': 'New Contents on Seezn',
        'author': 'pandamoon21',
        'items': items
    }