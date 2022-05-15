from rsshub.utils import fetch

domain = 'http://www.bjnews.com.cn'


def parse(post):
    item = {}
    item['description']  = item['title'] = post.css('a::text').extract_first()
    item['link'] = post.css('a::attr(href)').extract_first()
    return item


def ctx(category=''):
    r_url = f"{domain}/{category}"
    tree = fetch(r_url)
    html = tree.css('body')
    posts = tree.css('.list-a')
    channel_title = html.css('a.cur::text').extract_first()
    return {
        'title': channel_title,
        'link': r_url,
        'description': '新京报频道新闻',
        'author': 'hillerliao',
        'items': list(map(parse, posts)) 
    }