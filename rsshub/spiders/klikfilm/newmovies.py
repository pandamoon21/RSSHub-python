import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    item['title'] = f"{post['title']} - {post['type']}"
    item['description'] = "{a}<br>{b}".format(
        a=f"Access: {post['access']} - ID: {post['id']}",
        b=f"<img referrerpolicy='no-referrer' src={post.get('cover')}>"
    )
    item['link'] = f"https://klikfilm.com/v4/watch/{post['slug']}"
    return item


def ctx(section=''):
    DEFAULT_HEADERS.update({
        'Referer': 'https:/klikfilm.com',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Forwarded-For': '103.60.9.114'
    })
    url = 'https://klikfilm.com/v4/core/core_actions_get/film_more.php'
    posts = requests.post(
        url=url,
        data={
            "action": "highlights",
            "oid": "0",
            "data1": section
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['data']['film']
    items = list(map(parse, posts))
    return {
        'title': 'KlikFilm New Movies',
        'link': 'https://klikfilm.com',
        'description': 'New Movies on KlikFilm',
        'author': 'pandamoon21',
        'items': items
    }