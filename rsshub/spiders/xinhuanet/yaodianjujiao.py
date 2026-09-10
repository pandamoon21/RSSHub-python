from rsshub.spiders.xinhuanet.utils import parse_html as parse
from rsshub.utils import DEFAULT_HEADERS, fetch

domain = 'http://www.news.cn'


def ctx():
    url = f'{domain}'
    tree = fetch(url, headers=DEFAULT_HEADERS)
    posts = tree.select('#depth li a')
    return {
        'title': 'Xinhuanet - Highlights',
        'link': url,
        'description': 'Xinhuanet - Highlights',
        'author': 'flyingicedragon',
        'items': list(map(parse, posts)),
    }
