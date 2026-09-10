from rsshub.spiders.xinhuanet.utils import parse_html as parse
from rsshub.utils import DEFAULT_HEADERS, fetch

domain = 'http://www.news.cn'


def ctx():
    url = f'{domain}'
    tree = fetch(url, headers=DEFAULT_HEADERS)
    posts = tree.select('#latest li a')
    return {
        'title': 'Xinhuanet - Latest',
        'link': url,
        'description': 'Xinhuanet - Latest',
        'author': 'flyingicedragon',
        'items': list(map(parse, posts)),
    }
