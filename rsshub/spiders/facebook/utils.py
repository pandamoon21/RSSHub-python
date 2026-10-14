"""Shared helpers for the Facebook spiders (port of RSSHub's lib/routes/facebook/utils.ts).

Both Facebook routes go through Meta's public GraphQL "comet" endpoints rather than the
GraphQL Graph API. That means:

* No Graph API access token is required, but an authenticated session IS required.
  Set ``FACEBOOK_COOKIE`` to the ``c_user=...; xs=...`` pair from a logged-in browser.
* Requests go through ``curl_cffi`` impersonating Chrome. Plain ``requests`` is rejected
  with HTTP 400 on every HTML endpoint because of its TLS/JA3 fingerprint.
* Tokens (``lsd``, ``jazoest``, ``fb_dtsg``) are issued per page load and must be
  harvested from the target page — a locally generated ``lsd`` is not accepted.
* Responses are newline-delimited JSON (NDJSON), not a single JSON document.

Facebook also rate-limits aggressively. When a query is declined, this module raises
``FacebookRateLimited``, which the routes translate into HTTP 503.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone

from curl_cffi import requests as curl_requests

BASE_URL = 'https://www.facebook.com'
GRAPHQL_URL = f'{BASE_URL}/api/graphql/'
REQUEST_TIMEOUT = 30

# TLS fingerprint to present. Facebook rejects non-browser handshakes outright.
IMPERSONATE = 'chrome'

# Signals to Facebook that the request comes from the comet web client. These mirror the
# upstream relay-provider variables; omitting them makes the API return an error document.
PROVIDER_VARIABLES = {
    '__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider': False,
    '__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider': False,
    '__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider': False,
    '__relay_internal__pv__CometFeedStory_enable_social_bubblesrelayprovider': False,
    '__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider': False,
    '__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider': False,
    '__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider': False,
    '__relay_internal__pv__IsWorkUserrelayprovider': False,
    '__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider': False,
    '__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider': False,
    '__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider': True,
    '__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider': False,
    '__relay_internal__pv__CometFeedShareMedia_shouldPrefetchShareImagerelayprovider': False,
    '__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider': False,
    '__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider': False,
    '__relay_internal__pv__IsMergQAPollsrelayprovider': False,
    '__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider': True,
    '__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider': False,
    '__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider': 'AUTO_TRANSLATE',
    '__relay_internal__pv__CometUFIShareActionMigrationrelayprovider': True,
    '__relay_internal__pv__CometUFISingleLineUFIrelayprovider': False,
    '__relay_internal__pv__relay_provider_comet_ufi_ssr_seo_deferrelayprovider': True,
    '__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider': False,
    '__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider': 150,
    '__relay_internal__pv__StoriesShouldEnablePhotosensitiveContentWarningrelayprovider': False,
    '__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider': False,
    '__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider': False,
}

# Hardcoded Meta document IDs for the two queries. These are stable in practice but are the
# first thing to re-check when upstream starts returning errors.
DOC_IDS = {
    'page': '28844200915213260',    # ProfileCometTimelineFeedRefetchQuery
    'group': '28691921240463205',   # GroupsCometFeedRegularStoriesPaginationQuery
}

FRIENDLY_NAMES = {
    'page': 'ProfileCometTimelineFeedRefetchQuery',
    'group': 'GroupsCometFeedRegularStoriesPaginationQuery',
}

# Mirrors lib/utils/route-limit.ts: the candidate pool page size when no explicit limit is given.
DEFAULT_LIMIT = 21

# Upper bound on how many items we ask Facebook for. Without this a caller-supplied
# ?limit=100000 is forwarded upstream and reliably trips the rate limiter.
MAX_LIMIT = 100

# Retry policy for transient network faults (never for a definitive rejection).
MAX_ATTEMPTS = 3
RETRY_BACKOFF = 1.5

# XML 1.0 forbids most C0 control characters outright. A single one makes the whole feed
# unparseable, so they are stripped from every string injected into atom.xml.
_XML_ILLEGAL_RE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


class FacebookRateLimited(RuntimeError):
    """Raised when Facebook rejects a request (rate limit or IP-level block).

    Mapped to HTTP 503 at the route level so feed readers retry rather than caching
    a generic 500. Mirrors upstream RSSHub's `503 Service Unavailable` for this case.
    """


class FacebookSessionExpired(FacebookRateLimited):
    """Raised when FACEBOOK_COOKIE is missing or no longer authenticates.

    A subclass of FacebookRateLimited so routes handle both identically, while keeping
    the two distinguishable for logs and tests.
    """


class FacebookNotFound(RuntimeError):
    """Raised when a page/group/profile identifier cannot be resolved.

    A client error (HTTP 404), not a retryable upstream failure.
    """


def clean_xml(text):
    """Make a string safe to embed inside CDATA in atom.xml.

    Two distinct hazards:

    * ``]]>`` inside the payload would close the surrounding CDATA section early and
      spill arbitrary markup into the document.
    * XML 1.0 forbids most C0 control characters; one is enough to make the feed
      unparseable for every reader.
    """
    if text is None:
        return ''
    if not isinstance(text, str):
        text = str(text)
    return _XML_ILLEGAL_RE.sub('', text).replace(']]>', ']]&gt;')



def get_cookie():
    """Return the configured Facebook cookie, or None."""
    return os.environ.get('FACEBOOK_COOKIE') or None


def get_route_limit(limit=None, default=DEFAULT_LIMIT):
    """Coerce a caller-supplied limit to a sane positive int.

    Mirrors upstream's getRouteLimit: a non-positive or missing value yields the default.
    Additionally clamps to MAX_LIMIT so a hostile ?limit= cannot be forwarded upstream.
    The project's own filter_content narrows the result further via ?limit=.
    """
    try:
        requested = int(limit)
    except (TypeError, ValueError):
        return default
    if requested <= 0:
        return default
    return min(requested, MAX_LIMIT)


def _js_string_length(text):
    """Length of a JS string: UTF-16 code units, so astral chars count as 2."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _iter_utf16_codepoints(text):
    """Yield (utf16_offset, char) so offsets line up with Facebook's UTF-16 ranges."""
    offset = 0
    for ch in text:
        yield offset, ch
        offset += 2 if ord(ch) > 0xFFFF else 1


def _slice_utf16(text, start, length):
    """Slice by UTF-16 offsets, matching JS String.prototype.slice semantics."""
    start = max(0, start)
    end = start + max(0, length)
    out = []
    for offset, ch in _iter_utf16_codepoints(text):
        if offset >= end:
            break
        if offset >= start:
            out.append(ch)
    return ''.join(out)


def _insert_html_marks(text, marks):
    """Insert HTML tags at UTF-16 offsets in a single pass.

    `marks` is a list of (offset, html, is_closing). Tags at the same offset are emitted
    closing-first so nesting stays well formed (matching upstream's sort order).
    """
    grouped = {}
    for offset, html, is_closing in marks:
        grouped.setdefault(offset, []).append((is_closing, html))

    out = []
    for offset, ch in _iter_utf16_codepoints(text):
        if offset in grouped:
            # Closing tags (is_closing=True) sort first at a shared offset.
            for _closing, html in sorted(grouped[offset], key=lambda m: not m[0]):
                out.append(html)
        out.append(ch)
    # Any marks sitting at or past the final offset (e.g. end-of-text close tags).
    tail = max(_js_string_length(text), 0)
    if tail in grouped:
        for _closing, html in sorted(grouped[tail], key=lambda m: not m[0]):
            out.append(html)
    return ''.join(out)


# ---------------------------------------------------------------- renderers

def render_image(media):
    """Render a Facebook photo object as an <img> tag."""
    if not isinstance(media, dict):
        return ''
    image = (
        (media.get('photo_image') or {}).get('uri')
        or (media.get('image') or {}).get('uri')
        or (media.get('large_share_image') or {}).get('uri')
    )
    if not image:
        return ''
    caption = media.get('accessibility_caption') or ''
    return f'<img src="{image}" alt="{caption}">'


def render_video(video):
    """Render a Facebook video object as a <video> tag."""
    if not isinstance(video, dict):
        return ''
    legacy = video.get('videoDeliveryLegacyFields') or {}
    src = legacy.get('browser_native_hd_url') or legacy.get('browser_native_sd_url')
    if not src:
        return ''
    poster = ((video.get('preferred_thumbnail') or {}).get('image') or {}).get('uri') or ''
    return f'<video controls poster="{poster}" src="{src}"></video>'


def render_attachment(attachment):
    """Render a story attachment (media, link card, nested subattachments, events)."""
    if not isinstance(attachment, dict):
        return ''

    subattachments = attachment.get('all_subattachments')
    if subattachments:
        nodes = subattachments.get('nodes') or []
        return ''.join(render_attachment(node) for node in nodes)

    target = attachment.get('target')
    if target:
        cover = target.get('comet_cover_media_renderer') or {}
        if cover.get('cover_video'):
            cover_html = render_video(cover['cover_video'])
        else:
            cover_html = render_image((cover.get('cover_photo') or {}).get('photo'))
        details = '<br>'.join(
            part for part in (
                target.get('capitalized_day_time_sentence'),
                (target.get('event_place') or {}).get('contextual_name'),
                (attachment.get('description') or {}).get('text'),
            ) if part
        )
        url = target.get('url', '')
        name = target.get('name', '')
        return f'<p><a href="{url}">{name}</a>{f"<br>{details}" if details else ""}</p>{cover_html}'

    media = attachment.get('media')
    if isinstance(media, dict) and media.get('__typename') == 'Video':
        grid = media.get('video_grid_renderer') or {}
        return render_video(grid.get('video') or media)

    img = render_image(media)
    link = (((attachment.get('story_attachment_link_renderer') or {}).get('attachment')
             or {}).get('web_link') or {}).get('url')
    if link:
        title = (attachment.get('title_with_entities') or {}).get('text') or ''
        return f'<p><a href="{link}">{img}<br>{title}</a></p>'
    return img


def render_text(message):
    """Render a plain story message, converting embedded entity ranges into links."""
    if not isinstance(message, dict):
        return ''
    text = message.get('text') or ''
    ranges = sorted(message.get('ranges') or [], key=lambda r: r.get('offset', 0))

    html = ''
    position = 0
    for rng in ranges:
        entity = rng.get('entity') or {}
        url = entity.get('external_url') or entity.get('url')
        offset = rng.get('offset', 0)
        if not url or offset < position:
            continue
        # Match upstream: drop ranges that start at or past the end of the text.
        if offset >= _js_string_length(text):
            continue
        html += _slice_utf16(text, position, offset - position)
        label = _slice_utf16(text, offset, rng.get('length', 0))
        html += f'<a href="{url}">{label}</a>'
        position = offset + rng.get('length', 0)

    html += _slice_utf16(text, position, _js_string_length(text))
    return f'<p>{html.replace(chr(10), "<br>")}</p>'


BLOCK_TAGS = {
    'HEADER_ONE': 'h1',
    'HEADER_TWO': 'h2',
    'HEADER_THREE': 'h3',
    'BLOCKQUOTE': 'blockquote',
    'UNORDERED_LIST_ITEM': 'li',
    'ORDERED_LIST_ITEM': 'li',
}

INLINE_TAGS = {
    'BOLD': 'b',
    'ITALIC': 'i',
    'UNDERLINE': 'u',
    'STRIKETHROUGH': 's',
}


def render_rich_block(block):
    """Render one rich-text block, applying inline style ranges as nested tags."""
    text = block.get('text') or ''
    marks = []
    for rng in block.get('inline_style_ranges') or []:
        tag = INLINE_TAGS.get(rng.get('inline_style'))
        if not tag:
            continue
        offset = rng.get('offset', 0)
        marks.append((offset, f'<{tag}>', False))
        marks.append((offset + rng.get('length', 0), f'</{tag}>', True))

    chars = _insert_html_marks(text, marks)
    tag = BLOCK_TAGS.get(block.get('block_type'), 'p')
    return f'<{tag}>{chars}</{tag}>'


def render_story(story):
    """Render a story into {'text': plain text or None, 'html': full HTML}."""
    section = story.get('comet_sections', {}).get('message') or {}
    message = section.get('story', {}).get('message') or story.get('message')

    rich = section.get('rich_message')
    if rich:
        text_html = ''.join(render_rich_block(block) for block in rich)
    elif message:
        text_html = render_text(message)
    else:
        text_html = ''

    attachments = ''.join(
        render_attachment((att.get('styles') or {}).get('attachment'))
        for att in story.get('attachments') or []
    )
    return {'text': (message or {}).get('text'), 'html': text_html + attachments}


# ---------------------------------------------------------------- traversal

def collect_stories(value, stories):
    """Depth-first walk, collecting every node whose __typename is 'Story'.

    Descends through both dicts and lists — GraphQL responses nest story nodes inside
    lists (feed edges, nodes arrays), so walking dict values alone misses everything.
    """
    if isinstance(value, dict):
        if value.get('__typename') == 'Story':
            stories.append(value)
            return
        for child in value.values():
            collect_stories(child, stories)
    elif isinstance(value, (list, tuple)):
        for child in value:
            collect_stories(child, stories)


def find_page_info(value):
    """Locate the first page_info object anywhere in the response tree."""
    if isinstance(value, dict):
        if value.get('page_info'):
            return value['page_info']
        for child in value.values():
            found = find_page_info(child)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = find_page_info(child)
            if found:
                return found
    return None



# ---------------------------------------------------------------- requests

def _new_session(cookie=None):
    """Create a curl_cffi session impersonating Chrome.

    Callers should normally use :func:`_get_session`, which reuses one session per cookie
    so the TLS handshake and connection pool are not rebuilt on every request.
    """
    session = curl_requests.Session(impersonate=IMPERSONATE)
    session.headers.update({
        'accept-language': 'en-US,en;q=0.9',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'document',
        'upgrade-insecure-requests': '1',
    })
    if cookie:
        session.headers['cookie'] = cookie
    return session


# One session per cookie across the process. Rebuilding the TLS handshake per request was
# pure overhead, and Facebook's cookies are refreshed server-side within a session.
_SESSION_LOCK = threading.Lock()
_SESSIONS = {}


def _get_session(cookie):
    """Return a cached session for this cookie, creating it on first use."""
    with _SESSION_LOCK:
        session = _SESSIONS.get(cookie)
        if session is None:
            session = _new_session(cookie)
            _SESSIONS[cookie] = session
        return session


def reset_sessions():
    """Drop cached sessions. Used by tests and after a session-expired response."""
    with _SESSION_LOCK:
        _SESSIONS.clear()


def _request_with_retry(session, method, url, **kwargs):
    """Perform a request, retrying transient network faults with backoff.

    Only connection-level failures are retried. A response that actually arrives is
    returned as-is: Facebook answering with a rejection is definitive and retrying it
    would deepen any rate limiting.
    """
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return getattr(session, method)(url, **kwargs)
        except Exception as exc:  # curl_cffi raises its own transport exceptions
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(RETRY_BACKOFF ** attempt)
    raise FacebookRateLimited(
        f'Network error talking to Facebook after {MAX_ATTEMPTS} attempts: '
        f'{type(last_error).__name__}: {last_error}'
    )


def extract_tokens(html):
    """Pull the request tokens Facebook issues per page load.

    A locally generated `lsd` is NOT accepted: the GraphQL call then returns an empty
    body or `missing_required_variable_value`. The tokens are scoped to one page load,
    so they must be harvested from the same page we are about to query.
    """
    lsd = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', html)
    jazoest = re.search(r'jazoest=(\d+)', html)
    dtsg = re.search(r'"DTSGInitialData",\[\],\{"token":"([^"]+)"', html)
    return {
        'lsd': lsd.group(1) if lsd else None,
        'jazoest': jazoest.group(1) if jazoest else None,
        'fb_dtsg': dtsg.group(1) if dtsg else None,
    }


def feed_requires_cookie():
    """Raise unless a FACEBOOK_COOKIE is configured."""
    if not get_cookie():
        raise FacebookSessionExpired(
            'FACEBOOK_COOKIE is not set. Facebook requires an authenticated session for '
            'this route; set FACEBOOK_COOKIE to the "c_user=...; xs=..." pair taken from '
            'a logged-in browser.'
        )


def bootstrap_tokens(session, url):
    """Load `url` and return the per-page-load tokens, or raise.

    A login redirect (or a page with no lsd) means the stored cookie no longer
    authenticates, which is a different problem from being rate limited.
    """
    page = _request_with_retry(session, 'get', url, timeout=REQUEST_TIMEOUT)
    if page.status_code != 200:
        raise FacebookRateLimited(
            f'Could not load {url} to obtain request tokens (HTTP {page.status_code}).'
        )

    tokens = extract_tokens(page.text)
    if not tokens['lsd']:
        raise FacebookSessionExpired(
            f'No lsd token on {url} — FACEBOOK_COOKIE is missing, expired, or was '
            'logged out. Export a fresh "c_user=...; xs=..." pair.'
        )
    return tokens


def fetch_stories(friendly_name, doc_id, variables, limit, page_url=None):
    """POST a comet GraphQL query and return the parsed Story nodes.

    Raises FacebookSessionExpired when the cookie is unusable, and FacebookRateLimited
    when Facebook declines the query for any other reason (rate limit, rotated doc_id).
    """
    feed_requires_cookie()
    session = _get_session(get_cookie())

    # Tokens are scoped to a page load, so bootstrap by loading the target page first.
    bootstrap_url = page_url or f'{BASE_URL}/me'
    tokens = bootstrap_tokens(session, bootstrap_url)

    payload = {
        'lsd': tokens['lsd'],
        'jazoest': tokens['jazoest'] or '',
        'fb_api_req_friendly_name': friendly_name,
        'variables': json.dumps({
            **PROVIDER_VARIABLES,
            **variables,
            'count': limit,
            'cursor': None,
            'scale': 1,
            'useDefaultActor': False,
        }),
        'doc_id': doc_id,
    }
    if tokens['fb_dtsg']:
        payload['fb_dtsg'] = tokens['fb_dtsg']

    res = _request_with_retry(
        session,
        'post',
        GRAPHQL_URL,
        data=payload,
        headers={
            'content-type': 'application/x-www-form-urlencoded',
            'x-fb-lsd': tokens['lsd'],
            'x-fb-friendly-name': friendly_name,
            'origin': BASE_URL,
            'referer': bootstrap_url,
            'accept': '*/*',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
        },
        timeout=REQUEST_TIMEOUT,
    )
    text = res.text

    stories = []
    page_info = None
    for line in text.split('\n'):
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        collect_stories(data, stories)
        if page_info is None:
            page_info = find_page_info(data)

    if page_info is None:
        raise _graphql_rejection(text, friendly_name, doc_id)
    return stories


# Facebook signals a stale doc_id / friendly name with these markers. Retrying or
# re-exporting the cookie does not help; the route needs a code update.
# Stored already-normalized (lowercase, no spaces/hyphens) to match _graphql_rejection.
_DOC_ID_MARKERS = (
    'unknowndocumentid',
    'invaliddocumentid',
    'documentnotfound',
    'unknownfield',
    'missingrequiredvariablevalue',
    'querynotfound',
)

# Markers indicating the stored cookie no longer authenticates.
_LOGIN_MARKERS = (
    'login',
    'checkpoint',
    'nologgedinuser',
    'requirelogin',
    'sessionexpired',
)


def _graphql_rejection(text, friendly_name, doc_id):
    """Build the most accurate exception for a declined GraphQL response."""
    message = ''
    try:
        errors = json.loads(text).get('errors') or []
        if errors:
            message = errors[0].get('message') or ''
    except (json.JSONDecodeError, AttributeError, IndexError):
        pass

    # Compare on a normalized form: Facebook writes "log in", "login" and "log-in"
    # interchangeably, so plain substring checks produce false negatives.
    lowered = re.sub(r'[\s\-_]+', '', message.lower())

    if any(marker in lowered for marker in _DOC_ID_MARKERS):
        # A code-level problem, not an operator-level one. Say so explicitly so nobody
        # wastes time re-exporting cookies.
        return FacebookRateLimited(
            f'Facebook rejected {friendly_name} with doc_id {doc_id!r}: {message!r}. '
            'This means the hardcoded doc_id in DOC_IDS has rotated and the spider needs '
            'updating — see the module docstring.'
        )

    if any(marker in lowered for marker in _LOGIN_MARKERS):
        return FacebookSessionExpired(
            f'Facebook requires a login for this request: {message!r}. '
            'Refresh FACEBOOK_COOKIE with a fresh "c_user=...; xs=..." pair.'
        )

    detail = f' Facebook said: {message!r}.' if message else ''
    if not text.strip():
        detail += ' The response body was empty, which usually means rate limiting.'
    return FacebookRateLimited(
        'Facebook declined the GraphQL request. This is usually rate limiting, an expired '
        f'FACEBOOK_COOKIE, or a rotated doc_id.{detail} '
        f'Response started with: {text[:200]!r}'
    )


def parse_timestamp(value):
    """Convert a Facebook unix-seconds timestamp to the project's YYYY-MM-DD HH:mm:ss.

    Non-positive values are rejected: Facebook uses 0/-1 as sentinels and formatting
    them would emit a misleading 1970 (or 1969) date for posts of unknown age.
    """
    if not value:
        return None
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except (OverflowError, OSError, ValueError):
        return None


def stories_to_items(stories):
    """Convert Story nodes into the spider item dicts.

    Every string is passed through clean_xml: the template injects these with |safe
    inside CDATA, so upstream text containing `]]>` or XML-illegal control characters
    would otherwise corrupt the whole feed.
    """
    items = []
    for node in stories:
        story = (node.get('comet_sections') or {}).get('content', {}).get('story') or {}
        own = render_story(story)
        attached = story.get('attached_story')
        shared = render_story(attached) if attached else None

        actors = node.get('actors') or [{}]
        author = actors[0].get('name') or ''

        items.append({
            'title': clean_xml(own.get('text') or (shared or {}).get('text') or author),
            'description': clean_xml(own.get('html', '') + ((shared or {}).get('html') or '')),
            'link': node.get('permalink_url', '') or '',
            'pubDate': parse_timestamp(node.get('creation_time')),
            'author': clean_xml(author),
        })
    return items


def resolve_group_id(group):
    """Resolve a group username to its numeric ID via the public about page."""
    session = _get_session(get_cookie())
    res = _request_with_retry(
        session,
        'get',
        f'{BASE_URL}/groups/{group}/about',
        headers={'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'},
        timeout=REQUEST_TIMEOUT,
    )
    match = re.search(r'"groupID":"(\d+)"', res.text)
    if not match:
        raise FacebookNotFound(f'Facebook group {group!r} not found (or it is not public).')
    return match.group(1)


def resolve_page_id(page):
    """Resolve a page/profile username to its numeric ID via the plugins page."""
    session = _get_session(get_cookie())
    res = _request_with_retry(
        session,
        'get',
        f'{BASE_URL}/plugins/page.php',
        params={'href': f'{BASE_URL}/{page}/'},
        timeout=REQUEST_TIMEOUT,
    )
    match = (
        re.search(r'initializeClickLoggers",\[[^\]]*\],\[false,"(\d+)"', res.text)
        or re.search(r'"pageID":"(\d+)"', res.text)
    )
    if not match:
        raise FacebookNotFound(f'Facebook page or profile {page!r} not found.')
    return match.group(1)

# ---------------------------------------------------------------- marketplace

def _iter_json_objects_containing(text, needle):
    """Yield parsed JSON objects that contain `needle`, via brace matching.

    Marketplace listings are embedded in the page HTML as nested JSON rather than
    behind a stable GraphQL doc_id (those are loaded from JS bundles), so we locate
    them by scanning for a known key and expanding to the enclosing object.
    """
    for match in re.finditer(re.escape(needle), text):
        depth = 0
        start = None
        for i in range(match.start(), -1, -1):
            ch = text[i]
            if ch == '}':
                depth += 1
            elif ch == '{':
                if depth == 0:
                    start = i
                    break
                depth -= 1
        if start is None:
            continue

        depth = 0
        end = None
        for i in range(start, len(text)):
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            continue
        try:
            yield json.loads(text[start:end])
        except json.JSONDecodeError:
            continue


def fetch_marketplace_listings(query, limit=DEFAULT_LIMIT, location=None):
    """Scrape Marketplace search results for `query`.

    Returns a list of raw listing dicts. Raises FacebookSessionExpired when no cookie is
    configured and FacebookRateLimited when the search page cannot be loaded.
    """
    query = (query or '').strip()
    if not query:
        raise FacebookNotFound('A Marketplace search query is required.')

    feed_requires_cookie()
    session = _get_session(get_cookie())
    url = f'{BASE_URL}/marketplace/search/'

    page = _request_with_retry(
        session, 'get', url, params={'query': query}, timeout=REQUEST_TIMEOUT
    )
    if page.status_code != 200:
        raise FacebookRateLimited(
            f'Facebook Marketplace search failed (HTTP {page.status_code}).'
        )
    if 'marketplace' not in page.text.lower():
        raise FacebookSessionExpired(
            'The Marketplace search page did not render any listings data. '
            'FACEBOOK_COOKIE is likely expired or logged out.'
        )

    # Restrict scanning to the search-results payload. Listing JSON also appears
    # elsewhere on the page (recommendations, prefetch stubs), and those must not leak
    # into the feed as phantom results.
    anchor = page.text.find('"marketplace_search')
    region = page.text[anchor:] if anchor != -1 else page.text

    # Facebook serves a synthetic placeholder listing when a search matches nothing
    # (observed: a "Nike P-6000" item with the obviously fake price "Rp123.456").
    # There is no "no results" flag to test, so require the title to relate to the
    # query. This also drops unrelated recommendations for genuine searches.
    terms = [t for t in re.split(r'[^\w]+', query.lower()) if len(t) > 1]

    listings = []
    seen = set()
    for obj in _iter_json_objects_containing(region, 'marketplace_listing_title'):
        title = obj.get('marketplace_listing_title')
        listing_id = obj.get('id')
        if not title or not listing_id or listing_id in seen:
            continue
        if terms and not any(term in title.lower() for term in terms):
            continue
        seen.add(listing_id)
        listings.append(obj)
        if len(listings) >= limit:
            break
    return listings


def marketplace_to_items(listings):
    """Convert raw Marketplace listing dicts into spider items.

    Listings missing an id or title are dropped rather than emitted as empty entries
    (the raw payload contains prefetch stubs and partial objects). All strings go
    through clean_xml for the same reason as stories_to_items.
    """
    items = []
    for listing in listings:
        if not isinstance(listing, dict):
            continue
        listing_id = listing.get('id')
        title = (listing.get('marketplace_listing_title') or '').strip()
        if not listing_id or not title:
            continue

        price = (listing.get('listing_price') or {}).get('formatted_amount') or ''
        city = ((listing.get('location') or {}).get('reverse_geocode') or {}).get('city') or ''

        parts = []
        if price:
            parts.append(f'<b>{clean_xml(price)}</b>')
        if city:
            parts.append(f'Location: {clean_xml(city)}')
        if listing.get('is_sold'):
            parts.append('SOLD')
        elif listing.get('is_pending'):
            parts.append('PENDING')

        photo = listing.get('primary_listing_photo') or {}
        image = (photo.get('image') or {}).get('uri') or (photo.get('photo_image') or {}).get('uri')
        if image:
            parts.append(f"<img referrerpolicy='no-referrer' src='{clean_xml(image)}'>")

        seller = (listing.get('marketplace_listing_seller') or {}).get('name') or ''

        items.append({
            'title': clean_xml(title),
            'description': '<br>'.join(parts),
            'link': f'{BASE_URL}/marketplace/item/{listing_id}/',
            'pubDate': parse_timestamp(listing.get('creation_time')),
            'author': clean_xml(seller) or 'Facebook Marketplace',
        })
    return items
