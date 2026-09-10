from rsshub.utils import fetch

domain = 'http://www.dxzq.net'


def parse(post):
    item = {}
    a = post.select_one('a')
    if a:
        item['description'] = item['title'] = a.get_text().strip()
        item['link'] = f"{domain}{a.get('href', '')}"
    span = post.select_one('span.time')
    item['pubDate'] = span.get_text().strip() if span else ''
    return item


def ctx(category=''):
    url = f"{domain}/main/zcgl/zxgg/index.shtml?catalogId=1,5,228"
    tree = fetch(url)
    if not tree:
         return {
            'title': 'Dongxing Asset Management - Latest Product Announcements',
            'link': url,
            'description': 'Dongxing Asset Management - Latest Product Announcements',
            'author': 'hillerliao',
            'items': []
        }
    posts = tree.select('.news_list li')
    return {
        'title': 'Dongxing Asset Management - Latest Product Announcements',
        'link': url,
        'description': 'Dongxing Asset Management - Latest Product Announcements',
        'author': 'hillerliao',
        'items': list(map(parse, posts)) 
    }