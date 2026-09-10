import hashlib
import urllib.parse

import arrow
import requests

from rsshub.utils import DEFAULT_HEADERS

# Keep the timeout below typical serverless gateway limits (e.g. Vercel's 10s)
# so a slow/unreachable upstream returns an empty feed instead of a 504.
REQUEST_TIMEOUT = 8

# www.cls.cn is blocked from some overseas/cloud IP ranges; m.cls.cn is served
# from different WAF nodes and accepts the same API + signature, so try it first.
HOSTS = ['m.cls.cn', 'www.cls.cn']


def generate_sign(params):
    """Sign CLS API requests (sorted query -> SHA1 -> MD5)."""
    query_string = urllib.parse.urlencode(sorted(params.items(), key=lambda x: x[0]))
    sha1_hash = hashlib.sha1(query_string.encode('utf-8')).hexdigest()
    return hashlib.md5(sha1_hash.encode('utf-8')).hexdigest()


def parse(post):
    item = {
        'title': post.get('title') or post.get('brief') or '',
        'description': post.get('content') or post.get('brief') or '',
        'link': post.get('shareurl') or f"https://www.cls.cn/detail/{post.get('id', '')}",
        'author': post.get('author') or '财联社',
        'pubDate': '',
    }
    try:
        item['pubDate'] = arrow.get(int(post.get('ctime') or 0)).isoformat()
    except (ValueError, TypeError):
        item['pubDate'] = arrow.now().isoformat()
    return item


def _matches_category(post, category):
    """Match an article against a subject name or numeric subject id."""
    if not category:
        return True
    if str(category).isdigit():
        return any(str(s.get('subject_id')) == str(category) for s in post.get('subjects') or [])
    needle = str(category).lower()
    return any(needle in str(s.get('subject_name', '')).lower() for s in post.get('subjects') or [])


def ctx(category=''):
    params = {
        'app': 'CailianpressWeb',
        'category': '',
        'os': 'web',
        'rn': '50',
        'last_time': '0',
    }
    params['sign'] = generate_sign(params)

    posts = []
    errors = []
    for host in HOSTS:
        try:
            res = requests.get(
                f'https://{host}/v1/roll/get_roll_list',
                headers=DEFAULT_HEADERS,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            res.raise_for_status()
            posts = (res.json().get('data') or {}).get('roll_data') or []
            if posts:
                break
        except Exception as e:
            errors.append(f'{host}: {e}')

    items = []
    for post in posts:
        if not _matches_category(post, category):
            continue
        try:
            items.append(parse(post))
        except Exception:
            continue

    title = f'{category} - Subjects - CLS' if category else 'Subjects - CLS'
    return {
        'title': title,
        'link': f'https://www.cls.cn/subject/{category}' if category else 'https://www.cls.cn',
        'description': title,
        'author': 'hillerliao',
        'items': items,
    }
