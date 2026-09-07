import time
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from rsshub.utils import fetch_with_deadline

domain = 'https://www.bjnews.com.cn'
m_domain = 'https://m.bjnews.com.cn'

# 总抓取预算(秒):尽量贴近 Vercel 10s 上限但留出冷启动/渲染余量。
#
# 网络背景:新京报对部分海外机房(Vercel 的 AWS 出口,当前区域 hkg1)呈"间歇性黑洞"——
# 大多时候 TCP 连接无响应直到超时,偶尔几秒内正常。m.bjnews.com.cn 同理。
# 单源硬等容易整套超时 500。因此采用三级接力 + 短超时快速切换:
#   ① www 桌面站 HTML(最新)
#   ② m 站 JSON 列表接口(与 www 不同线路,提高撞中可用出口概率)
#   ③ r.jina.ai reader 中转(其服务端非云厂商被封锁段,实测可抓取新京报)
# 全程在 REQUEST_BUDGET 内;每源用短 deadline,失败立即切下一源。
REQUEST_BUDGET = 8.0
SLICE = 2.2  # 直连源单轮预算;黑洞下快速失败换源,成功响应多在 1~3s 内

# jina reader 免费中转(无 key 限速约 20 次/分,对 RSS 轮询足够)
JINA = 'https://r.jina.ai'

# 频道元信息:category -> (m站 channel_id, 中文名)
# m站接口 /bwnew/index-tj 需要 channel_id;名称用于 API 兜底时的 feed 标题。
CHANNELS = {
    'video': (90, '视频'),
    'depth': (97, '深读'),
    'gongyi': (10022, '公益'),
    'diyikandian': (10010, '第一看点'),
    'news': (101, '时事'),
    'beijing': (4, '北京'),
    'guoji': (10008, '国际'),
    'zhengshi': (10016, '政事儿'),
    'point': (5, '观点'),
    'industrial': (92, '消费'),
    'entertainment': (8, '娱乐'),
    'culture': (7, '文化'),
    'sports': (9, '体育'),
    'education': (12, '京彩教育'),
    'financial': (6, '浪花资本'),
    'technology': (16, '藻知科技'),
    'kunlunzhiku': (10053, '鲲纶智库'),
    'car': (10, '潮流智造局'),
    'estate': (11, '城市好望角'),
    'shenghuoshe': (10052, '海星生活社'),
    'photo': (14, '图说'),
    'thinktank': (94, '智库'),
    'shuju': (10011, '数据'),
    'country': (93, '乡村'),
    'beikecaijingapp': (10047, '贝壳财经客户端'),
}


def _clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def _m_channel(category):
    """(channel_id, 中文名);未知频道 id 返回 None。"""
    meta = CHANNELS.get(category)
    return (meta if meta else (None, category))


def parse_desktop(res):
    """解析桌面站瀑布流列表,返回 item 列表。"""
    tree = BeautifulSoup(res.text, 'html.parser')
    posts = tree.select('#waterfall-container .pin_demo > a')
    if not posts:
        raise ValueError('解析为空(页面结构可能已变更)')

    def parse(post):
        item = {}
        text = _clean(post.get_text())
        item['description'] = item['title'] = text
        item['link'] = post['href']
        return item

    return list(map(parse, posts))


def parse_mapi(res):
    """解析 m站 JSON 列表接口,返回 item 列表。"""
    payload = res.json()
    if not (isinstance(payload, dict) and str(payload.get('status')) == '1'
            and payload.get('info') == 'ok'):
        raise ValueError(f'm站接口返回异常: {str(payload)[:100]}')
    items = []
    for d in payload.get('data') or []:
        title = _clean(d.get('title', ''))
        if not title:
            continue
        du = d.get('detail_url') or {}
        link = du.get('pc_url') or du.get('m_url')
        if not link:
            uuid = d.get('uuid')
            if not uuid:
                continue
            link = f'{domain}/detail/{uuid}.html'
        item = {'title': title, 'description': title, 'link': link}
        try:
            pt = d.get('publish_time')
            dt = datetime.strptime(pt, '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
            item['pubDate'] = dt.isoformat()
        except Exception:
            pass
        items.append(item)
    if not items:
        raise ValueError('m站接口未返回有效条目')
    return items


def parse_jina(res):
    """解析 r.jina.ai 中转返回的 markdown 文本,提取文章链接。"""
    text = res.text
    items = []
    seen = set()
    # jina 会把页面 <a href> 转成 markdown 链接;仅收 bjnews 文章详情页
    pat = re.compile(
        r'\[([^\]]{4,150})\]'
        r'\((https?://(?:www\.|m\.)?bjnews\.com\.cn/(?:detail-\d+\.html|detail/\d+\.html))\)')
    for m in pat.finditer(text):
        title = _clean(m.group(1))
        url = m.group(2).strip()
        if not title or url in seen:
            continue
        seen.add(url)
        items.append({'title': title, 'description': title, 'link': url})
    if not items:
        raise ValueError('jina 中转文本未解析出文章链接')
    return items


def _fetch(category):
    """预算内三级接力抓取:桌面站 HTML → m站 JSON → jina 中转;失败快速切换。

    全部失败则抛异常(不吞错,防止坏数据进 SWR 缓存)。
    """
    start = time.time()
    errors = []
    r_url = f'{domain}/{category}'
    channel_id, channel_name = _m_channel(category)
    api_url = None

    # 未知频道:先以短请求探测 m 页里隐藏的 channel_id(供源2使用)
    if channel_id is None:
        try:
            page = fetch_with_deadline(f'{m_domain}/{category}',
                                       deadline=min(2.0, REQUEST_BUDGET), timeout=3.0)
            m = re.search(r"id=['\"]cur_channel_id['\"][^>]*value=['\"](\d+)", page.text)
            if m:
                channel_id = int(m.group(1))
        except Exception as e:
            errors.append(f'探测channel_id: {e}')
    if channel_id:
        api_url = (f'{m_domain}/bwnew/index-tj?page=1&size=20'
                   f'&channel_id={channel_id}&wz_id=1')

    candidates = [('desktop', r_url, parse_desktop)]
    if api_url:
        candidates.append(('mapi', api_url, parse_mapi))
    candidates.append(('jina', f'{JINA}/{r_url}', parse_jina))

    for name, url, parser in candidates:
        remaining = REQUEST_BUDGET - (time.time() - start)
        if remaining < 1.2:
            errors.append(f'{name}: 预算耗尽(剩余{remaining:.1f}s)')
            break
        deadline = remaining if name == 'jina' else min(SLICE, remaining)
        try:
            res = fetch_with_deadline(url, deadline=deadline, timeout=deadline + 1.0)
            items = parser(res)
            if not items:
                raise ValueError('解析为空')
            print(f'[bjnews] {category}: 源 {name} 成功 '
                  f'({time.time() - start:.1f}s, {len(items)} 条)')
            return items, channel_name, r_url
        except Exception as e:
            errors.append(f'{name}: {e}')
            print(f'[bjnews] {category}: 源 {name} 失败 '
                  f'({time.time() - start:.1f}s): {e}')

    raise RuntimeError(f'新京报「{category}」抓取失败: ' + ' | '.join(errors))


def ctx(category=''):
    items, channel_name, r_url = _fetch(category)
    return {
        'title': f'{channel_name} - 新京报',
        'link': r_url,
        'description': f'新京报「{channel_name}」频道新闻',
        'author': 'hillerliao',
        'items': items,
    }
