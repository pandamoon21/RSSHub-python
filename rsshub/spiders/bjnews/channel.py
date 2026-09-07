import time
import re
import requests
from bs4 import BeautifulSoup
from rsshub.utils import fetch_with_deadline

domain = 'https://www.bjnews.com.cn'

# 总抓取预算(秒):尽量贴近 Vercel 10s 上限但留出冷启动/渲染余量。
# 实测新京报 CDN 对海外机房(如 Vercel 函数地域)普遍"慢但活着":正常响应常需
# 3~9s。若像 6s 版本那样收紧预算,会把大量"慢速能成功"的请求提前掐死——这是
# 之前"更新后抓不到"的根因,必须放回足够宽的时间窗。
REQUEST_BUDGET = 8.0
# 第一轮在多少秒内失败才算"快速失败"(疑似被 CDN 拒绝/连接黑洞)。
# 仅这种场景值得换连接重试(可能命中别的边缘节点);慢超时说明源在慢慢吐数据,
# 重开连接只会重置下载进度、白白浪费预算,所以不重试。
QUICK_FAIL_WINDOW = 3.0


def _clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def parse(post):
    item = {}
    text = _clean(post.get_text())
    item['description'] = item['title'] = text
    item['link'] = post['href']
    return item


def _fetch_page(url):
    """在预算内抓取;慢速超时直接放弃、快速失败则换连接重试;全部失败抛异常。

    抛异常(而不是返回空 feed)是关键:路由外层 SWR 缓存会缓存任何返回值,
    把失败吞成 200 会把错误文案写进缓存长期输出。抛异常则缓存层只会保留上一次
    成功的好数据,不会写入坏数据。
    """
    start = time.time()
    last_err = None
    for attempt in (1, 2):
        elapsed = time.time() - start
        if attempt == 2 and elapsed >= QUICK_FAIL_WINDOW:
            print(f'[bjnews] 慢速超时({elapsed:.1f}s),不再重试避免重置进度')
            break
        remaining = REQUEST_BUDGET - elapsed
        if remaining < 1.0:
            break
        try:
            res = fetch_with_deadline(url, deadline=remaining, timeout=REQUEST_BUDGET)
            return res
        except Exception as e:
            last_err = e
            print(f'[bjnews] 第 {attempt} 轮抓取失败({elapsed:.1f}s): {e}')
    raise RuntimeError(f'新京报页面抓取失败: {last_err}')


def ctx(category=''):
    r_url = f"{domain}/{category}"
    res = _fetch_page(r_url)
    tree = BeautifulSoup(res.text, 'html.parser')
    posts = tree.select('#waterfall-container .pin_demo > a')
    if not posts:
        raise RuntimeError(f'新京报页面解析为空(结构可能已变更): {r_url}')
    channel_title = _clean(tree.select('.cur')[0].get_text())
    return {
        'title': f'{channel_title} - 新京报',
        'link': r_url,
        'description': f'新京报「{channel_title}」频道新闻',
        'author': 'hillerliao',
        'items': list(map(parse, posts)),
    }
