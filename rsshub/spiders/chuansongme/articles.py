from rsshub.utils import fetch

domain = 'https://chuansongme.com'


def parse(post):
    item = {}
    a = post.select('a.question_link')
    if a:
        item['title'] = a[-1].get_text().strip()
        item['link'] = f"{domain}{a[-1].get('href', '')}"
    return item


def ctx(category=''):
    url = f"{domain}/{category}"
    tree = fetch(url)
    if not tree:
         return {
            'title': 'Chuansongme',
            'link': domain,
            'description': 'Chuansongme: WeChat Official Account subscription',
            'author': 'alphardex',
            'items': []
        }
    posts = tree.select('.feed_body .pagedlist_item')
    return {
        'title': 'Chuansongme',
        'link': domain,
        'description': 'Chuansongme: WeChat Official Account subscription',
        'author': 'alphardex',
        'items': list(map(parse, posts))
    }