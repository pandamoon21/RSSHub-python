import re
import functools
import threading
import hashlib
import pickle

import requests
from flask import Response, request, current_app
from parsel import Selector

import arrow

from rsshub.extensions import cache

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
}


class XMLResponse(Response):
    def __init__(self, response=None, *args, **kwargs):
        if (
            isinstance(response, str)
            and 'mimetype' not in kwargs
            and 'content_type' not in kwargs
            and 'contenttype' not in kwargs
            and response.startswith('<?xml')
        ):
            kwargs['mimetype'] = 'application/xml'
        return super().__init__(response, *args, **kwargs)


def fetch(url: str, headers: dict = DEFAULT_HEADERS, proxies: dict = None):
    """Fetch a URL and return a parsel Selector tree.

    Spiders rely on this helper to keep behavior consistent with the
    legacy parsel-based scraping pipeline.
    """
    try:
        res = requests.get(url, headers=headers, proxies=proxies)
        res.raise_for_status()
    except Exception as e:
        print(f'[Err] {e}')
        return None
    html = res.text
    tree = Selector(text=html)
    return tree


def filter_content(items):
    """Legacy regex-based filter (kept for the earnings spiders).

    Note: route-level filtering uses the `filter_content` template
    global defined in `rsshub.blueprints.main`.
    """
    content = []
    p1 = re.compile(r'(.*)(to|will|date|schedule) (.*)results', re.IGNORECASE)
    p2 = re.compile(r'(.*)(schedule|schedules|announce|to) (.*)call', re.IGNORECASE)
    p3 = re.compile(r'(.*)release (.*)date', re.IGNORECASE)

    for item in items:
        title = item['title']
        if p1.match(title) or p2.match(title) or p3.match(title):
            content.append(item)
    return content


def swr_cache(timeout=3600):
    """Stale-While-Revalidate cache decorator.

    If a cached value exists, return it immediately and trigger a
    debounced background refresh. Otherwise fetch synchronously and
    cache the result.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            key_data = (f.__name__, args, kwargs, request.path, request.args)
            key_hash = hashlib.md5(pickle.dumps(key_data)).hexdigest()
            cache_key = f"swr_cache:{key_hash}"

            cached_data = cache.get(cache_key)

            app = current_app._get_current_object()
            req_path = request.path
            req_query_string = request.query_string

            if cached_data:
                if not isinstance(cached_data, (tuple, list)):
                    print(
                        f"[SWR] Warning: cached_data for {req_path} "
                        f"is not iterable: {type(cached_data)} value={cached_data!r}"
                    )
                    cache.delete(cache_key)
                else:
                    try:
                        data, _timestamp = cached_data
                        lock_key = f"swr_lock:{key_hash}"
                        if not cache.get(lock_key):
                            print(f"[SWR] Triggering background refresh for {req_path}")
                            cache.set(lock_key, 1, timeout=60)
                            threading.Thread(
                                target=refresh_cache,
                                args=(
                                    app,
                                    req_path,
                                    req_query_string,
                                    cache_key,
                                    f,
                                    args,
                                    kwargs,
                                ),
                            ).start()
                        else:
                            print(f"[SWR] Refresh locked/debounced for {req_path}")
                        return data
                    except Exception as e:
                        print(
                            f"[SWR] ERROR in decorated_function unpacking "
                            f"for {req_path}: {e}"
                        )
                        cache.delete(cache_key)

            print(f"[SWR] Cache miss for {req_path}, fetching synchronously")
            result = f(*args, **kwargs)
            cache.set(
                cache_key,
                (result, arrow.now().timestamp()),
                timeout=timeout * 24 * 7,
            )
            return result

        return decorated_function

    return decorator


def refresh_cache(app, path, query_string, cache_key, func, args, kwargs):
    """Background task to refresh a SWR cache entry."""
    try:
        print(f"[SWR] Background refreshing {cache_key}")
        if isinstance(query_string, bytes):
            query_string = query_string.decode('utf-8')
        with app.test_request_context(path=path, query_string=query_string):
            result = func(*args, **kwargs)
            cache.set(
                cache_key,
                (result, arrow.now().timestamp()),
                timeout=86400 * 7,
            )
        print(f"[SWR] Background refresh successful for {cache_key}")
    except Exception as e:
        print(f"[SWR] Background refresh failed for {cache_key}: {e}")
