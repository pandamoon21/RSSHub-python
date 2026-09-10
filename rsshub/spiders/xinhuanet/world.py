from rsshub.spiders.xinhuanet.utils import parse_html as parse
from rsshub.utils import DEFAULT_HEADERS, fetch

domain = 'http://www.news.cn/world/index.html'


def ctx():
    url = f'{domain}'
    tree = fetch(url, headers=DEFAULT_HEADERS)
    posts = tree.select('#recommendDepth a')
    return {
        'title': 'Xinhuanet - World News',
        'link': url,
        'description': 'Xinhuanet - World News',
        'author': 'flyingicedragon',
        'items': list(map(parse, posts)),
    }
