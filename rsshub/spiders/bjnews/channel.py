import re

from bs4 import BeautifulSoup
from rsshub.utils import fetch_with_deadline

domain = 'http://www.bjnews.com.cn'

# 总耗时预算(秒):给 Vercel 10s 限制留出冷启动余量。
# 新京报 CDN 会对部分海外机房 IP 黑洞(连接挂起),裸 requests 没有总截止会
# 一直挂到 Vercel 上限才被掐断 -> 504。设硬截止可保证请求总能及时返回。
REQUEST_DEADLINE = 6.0
REQUEST_TIMEOUT = 5.0


def _clean(text):
    # HTML 源码的换行缩进会被 get_text() 带进结果,导致 title 前后出现多余换行/空格,
    # 统一折叠成普通空白并去除首尾。
    return re.sub(r'\s+', ' ', text).strip()


def parse(post):
    item = {}
    item['description'] = item['title'] = _clean(post.get_text())
    item['link'] = post['href']
    return item


def ctx(category=''):
    r_url = f"{domain}/{category}"
    try:
        res = fetch_with_deadline(r_url, deadline=REQUEST_DEADLINE, timeout=REQUEST_TIMEOUT)
        tree = BeautifulSoup(res.text, 'html.parser')
        posts = tree.select('#waterfall-container .pin_demo > a')
        channel_title = tree.select('.cur')[0].get_text().strip()
        items = list(map(parse, posts))
    except Exception as e:
        print(f'[bjnews/{category}] 页面获取失败: {e}')
        return {
            'title': f'新京报 - {category}',
            'link': r_url,
            'description': f'新京报「{category}」频道新闻 (页面暂时无法获取，请稍后重试)',
            'author': 'hillerliao',
            'items': [],
        }

    return {
        'title': f'{channel_title} - 新京报',
        'link': r_url,
        'description': f'新京报「{channel_title}」频道新闻',
        'author': 'hillerliao',
        'items': items,
    }
