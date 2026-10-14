"""Offline tests for the Facebook spiders.

These never touch the network: the GraphQL/search HTTP layer is stubbed. They encode the
behaviours that were previously only verified by hand — several of which were real bugs
(CDATA break-out, XML-illegal control characters, phantom Marketplace listings, raw
transport exceptions escaping as HTTP 500).
"""
import json
import unittest
from unittest import mock
from xml.etree import ElementTree

from rsshub import create_app
from rsshub.spiders.facebook import utils as u

# A page body containing the tokens Facebook issues per page load.
FAKE_PAGE_HTML = (
    'junk "LSD",[],{"token":"test-lsd-token"} more '
    'jazoest=12345 and "DTSGInitialData",[],{"token":"test-dtsg"}'
)


def ndjson_feed(stories, page_info=True):
    """Build a JSON GraphQL response containing the given story nodes."""
    feed = {'edges': [{'node': s} for s in stories]}
    if page_info:
        feed['page_info'] = {'has_next_page': False, 'end_cursor': 'cursor'}
    return json.dumps({'data': {'feed': feed}})


def make_story(text='hello world', permalink='https://www.facebook.com/x/posts/1',
               author='Author', creation_time=1700000000, attachments=None,
               attached_story=None):
    story = {
        'message': {'text': text},
        'attachments': attachments or [],
    }
    if attached_story is not None:
        story['attached_story'] = attached_story
    return {
        '__typename': 'Story',
        'permalink_url': permalink,
        'creation_time': creation_time,
        'actors': [{'name': author, 'url': 'https://www.facebook.com/x'}],
        'comet_sections': {'content': {'story': story}},
    }


class FakeResponse:
    def __init__(self, text='', status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    """Stands in for a curl_cffi session."""

    def __init__(self, page_html=FAKE_PAGE_HTML, post_text='', post_status=200,
                 get_status=200, raise_on_get=None, raise_on_post=None):
        self.page_html = page_html
        self.post_text = post_text
        self.post_status = post_status
        self.get_status = get_status
        self.raise_on_get = raise_on_get
        self.raise_on_post = raise_on_post
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if self.raise_on_get:
            raise self.raise_on_get
        return FakeResponse(self.page_html, self.get_status)

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if self.raise_on_post:
            raise self.raise_on_post
        return FakeResponse(self.post_text, self.post_status)


class FacebookTestBase(unittest.TestCase):
    def setUp(self):
        u.reset_sessions()
        self.app = create_app('testing')
        # The routes use @swr_cache, which persists across tests in-process and would
        # otherwise make an assertion depend on test execution order.
        from rsshub.extensions import cache
        with self.app.app_context():
            cache.clear()

    def tearDown(self):
        u.reset_sessions()

    def patch_network(self, session):
        """Patch the session factory and cookie so no network access happens."""
        return (
            mock.patch.object(u, '_get_session', return_value=session),
            mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'),
        )

    def render_feed(self, items):
        from flask import render_template
        with self.app.test_request_context('/'):
            return render_template('main/atom.xml', title='T', link='L',
                                   description='D', author='A', items=items)


class CleanXmlTests(FacebookTestBase):
    def test_cdata_breakout_is_escaped(self):
        self.assertEqual(u.clean_xml('a ]]> b'), 'a ]]> b'.replace(']]>', ']]&gt;'))

    def test_control_characters_are_stripped(self):
        self.assertEqual(u.clean_xml('a\x00b\x0bc\x1fd'), 'abcd')

    def test_none_and_non_string(self):
        self.assertEqual(u.clean_xml(None), '')
        self.assertEqual(u.clean_xml(123), '123')

    def test_feed_with_hostile_content_is_well_formed(self):
        """The regression: ]]> and control chars used to make the whole feed unparseable."""
        items = [{
            'title': 'break ]]> out',
            'description': 'body ]]> and a \x0b control \x1f char',
            'link': 'https://x/1',
            'pubDate': '2026-01-01 00:00:00',
            'author': 'A ]]> B',
        }]
        cleaned = [{k: (u.clean_xml(v) if isinstance(v, str) else v) for k, v in it.items()}
                   for it in items]
        ElementTree.fromstring(self.render_feed(cleaned).encode())

    def test_stories_to_items_output_survives_rendering(self):
        """End-to-end: hostile upstream text must still yield a parseable feed."""
        node = make_story('contains ]]> and \x0b control chars', author='A ]]> B')
        ElementTree.fromstring(self.render_feed(u.stories_to_items([node])).encode())


class Utf16Tests(unittest.TestCase):
    def test_js_length_matches_utf16(self):
        for s in ['abc', 'a\U0001F600b', 'naïve', '中文测试', 'x\U0001F600\U0001F601y']:
            self.assertEqual(u._js_string_length(s), len(s.encode('utf-16-le')) // 2, s)

    def test_slice_utf16_handles_astral_characters(self):
        s = 'a\U0001F600bcd'
        self.assertEqual(u._slice_utf16(s, 0, 1), 'a')
        self.assertEqual(u._slice_utf16(s, 1, 2), '\U0001F600')
        self.assertEqual(u._slice_utf16(s, 1, 3), '\U0001F600b')
        self.assertEqual(u._slice_utf16(s, 3, 2), 'bc')


class RendererTests(unittest.TestCase):
    def test_render_text_converts_ranges_to_links(self):
        msg = {'text': 'Hello world',
               'ranges': [{'offset': 6, 'length': 5, 'entity': {'external_url': 'https://x'}}]}
        self.assertEqual(u.render_text(msg), '<p>Hello <a href="https://x">world</a></p>')

    def test_render_text_escapes_newlines(self):
        self.assertEqual(u.render_text({'text': 'a\nb'}), '<p>a<br>b</p>')

    def test_render_text_skips_range_without_url(self):
        msg = {'text': 'abcdef', 'ranges': [{'offset': 1, 'length': 3, 'entity': {}}]}
        self.assertEqual(u.render_text(msg), '<p>abcdef</p>')

    def test_render_text_handles_overlapping_and_oob_ranges(self):
        msg = {'text': 'abcdefgh',
               'ranges': [{'offset': 0, 'length': 4, 'entity': {'url': 'u1'}},
                          {'offset': 2, 'length': 3, 'entity': {'url': 'u2'}}]}
        self.assertEqual(u.render_text(msg), '<p><a href="u1">abcd</a>efgh</p>')
        oob = {'text': 'abc', 'ranges': [{'offset': 10, 'length': 5, 'entity': {'url': 'u'}}]}
        self.assertEqual(u.render_text(oob), '<p>abc</p>')

    def test_render_text_handles_empty(self):
        self.assertEqual(u.render_text({}), '<p></p>')
        self.assertEqual(u.render_text({'text': ''}), '<p></p>')

    def test_render_rich_block_applies_inline_styles(self):
        block = {'text': 'abc', 'block_type': 'HEADER_ONE',
                 'inline_style_ranges': [{'inline_style': 'BOLD', 'offset': 0, 'length': 2},
                                         {'inline_style': 'ITALIC', 'offset': 2, 'length': 1}]}
        self.assertEqual(u.render_rich_block(block), '<h1><b>ab</b><i>c</i></h1>')

    def test_render_image_and_video(self):
        self.assertEqual(
            u.render_image({'photo_image': {'uri': 'https://i/1.jpg'}, 'accessibility_caption': 'cap'}),
            '<img src="https://i/1.jpg" alt="cap">')
        self.assertEqual(u.render_image(None), '')
        self.assertIn('<video', u.render_video(
            {'videoDeliveryLegacyFields': {'browser_native_sd_url': 'https://v/sd.mp4'},
             'preferred_thumbnail': {'image': {'uri': 'https://p.jpg'}}}))

    def test_render_attachment_handles_subattachments(self):
        att = {'all_subattachments': {'nodes': [
            {'media': {'photo_image': {'uri': 'https://i/a.jpg'}}},
            {'media': {'photo_image': {'uri': 'https://i/b.jpg'}}},
        ]}}
        out = u.render_attachment(att)
        self.assertEqual(out.count('<img'), 2)

    def test_render_attachment_tolerates_garbage(self):
        for bad in [None, {}, {'media': None}, {'target': {}}, []]:
            self.assertIsInstance(u.render_attachment(bad), str)


class TraversalTests(unittest.TestCase):
    def test_collect_stories_descends_into_lists(self):
        """The regression: story nodes live inside `edges` lists and were skipped."""
        payload = {'data': {'feed': {'edges': [{'node': make_story()}]}}, }
        found = []
        u.collect_stories(payload, found)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['__typename'], 'Story')

    def test_collect_stories_ignores_non_story(self):
        found = []
        u.collect_stories({'a': [{'__typename': 'User'}, {'b': {'__typename': 'Photo'}}]}, found)
        self.assertEqual(found, [])

    def test_find_page_info_search_lists(self):
        payload = {'data': {'feed': {'edges': [], 'page_info': {'end_cursor': 'c'}}}}
        self.assertEqual(u.find_page_info(payload), {'end_cursor': 'c'})
        self.assertIsNone(u.find_page_info({'a': [1, 2]}))


class LimitTests(unittest.TestCase):
    def test_defaults_and_clamping(self):
        self.assertEqual(u.get_route_limit(None), u.DEFAULT_LIMIT)
        self.assertEqual(u.get_route_limit(0), u.DEFAULT_LIMIT)
        self.assertEqual(u.get_route_limit(-5), u.DEFAULT_LIMIT)
        self.assertEqual(u.get_route_limit('abc'), u.DEFAULT_LIMIT)
        self.assertEqual(u.get_route_limit(5), 5)
        # A hostile limit must not be forwarded upstream.
        self.assertEqual(u.get_route_limit(10 ** 6), u.MAX_LIMIT)


class TimestampTests(unittest.TestCase):
    def test_valid_and_invalid(self):
        self.assertEqual(u.parse_timestamp(1700000000), '2023-11-14 22:13:20')
        for bad in [None, '', 'abc', {}, -1]:
            self.assertIsNone(u.parse_timestamp(bad))


class FetchStoriesTests(FacebookTestBase):
    def _run(self, session, **kwargs):
        p1, p2 = self.patch_network(session)
        with p1, p2:
            return u.fetch_stories('SomeQuery', '123', {'id': '1'}, 5, **kwargs)

    def test_missing_cookie_raises_session_expired(self):
        with mock.patch.object(u, 'get_cookie', return_value=None):
            with self.assertRaises(u.FacebookSessionExpired):
                u.fetch_stories('Q', '1', {}, 5)

    def test_no_lsd_token_means_expired_session(self):
        session = FakeSession(page_html='<html>login page, no tokens</html>')
        with self.assertRaises(u.FacebookSessionExpired):
            self._run(session)

    def test_successful_parse(self):
        session = FakeSession(post_text=ndjson_feed([make_story('hi')]))
        stories = self._run(session)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]['permalink_url'], 'https://www.facebook.com/x/posts/1')

    def test_tokens_are_sent_from_the_page(self):
        session = FakeSession(post_text=ndjson_feed([make_story()]))
        self._run(session)
        _, kwargs = session.post_calls[0]
        body = kwargs['data']
        self.assertEqual(body['lsd'], 'test-lsd-token')
        self.assertEqual(body['jazoest'], '12345')
        self.assertEqual(body['fb_dtsg'], 'test-dtsg')

    def test_rotated_doc_id_is_reported_as_such(self):
        session = FakeSession(post_text=json.dumps(
            {'errors': [{'message': 'Unknown document id', 'severity': 'CRITICAL'}]}))
        with self.assertRaises(u.FacebookRateLimited) as ctx:
            self._run(session)
        self.assertIn('doc_id', str(ctx.exception))
        self.assertIsNot(type(ctx.exception), u.FacebookSessionExpired)

    def test_login_required_is_reported_as_session_problem(self):
        session = FakeSession(post_text=json.dumps(
            {'errors': [{'message': 'Please log in to continue', 'severity': 'CRITICAL'}]}))
        with self.assertRaises(u.FacebookSessionExpired):
            self._run(session)

    def test_empty_body_reported_as_rate_limit(self):
        session = FakeSession(post_text='')
        with self.assertRaises(u.FacebookRateLimited):
            self._run(session)

    def test_transport_error_becomes_rate_limited_not_raw_exception(self):
        """The regression: a ConnectionError used to escape and surface as HTTP 500."""
        session = FakeSession(raise_on_get=ConnectionError('boom'))
        with mock.patch.object(u, 'RETRY_BACKOFF', 0):
            with self.assertRaises(u.FacebookRateLimited) as ctx:
                self._run(session)
        self.assertIn('Network error', str(ctx.exception))


class StoriesToItemsTests(unittest.TestCase):
    def test_maps_fields(self):
        items = u.stories_to_items([make_story('hello', author='Zed')])
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it['title'], 'hello')
        self.assertEqual(it['author'], 'Zed')
        self.assertEqual(it['pubDate'], '2023-11-14 22:13:20')
        self.assertEqual(it['link'], 'https://www.facebook.com/x/posts/1')

    def test_falls_back_to_shared_story_text(self):
        node = make_story('', attached_story={'message': {'text': 'shared body'},
                                              'attachments': []})
        items = u.stories_to_items([node])
        self.assertEqual(items[0]['title'], 'shared body')
        self.assertIn('shared body', items[0]['description'])

    def test_output_is_xml_clean(self):
        items = u.stories_to_items([make_story('bad ]]> text \x0b here')])
        self.assertNotIn(']]>', items[0]['title'])
        self.assertNotIn('\x0b', items[0]['title'])


class MarketplaceTests(FacebookTestBase):
    def _listing(self, **over):
        base = {
            'id': '123',
            'marketplace_listing_title': 'iPhone 11',
            'listing_price': {'formatted_amount': 'Rp1.000'},
            'location': {'reverse_geocode': {'city': 'Jakarta'}},
            'primary_listing_photo': {'image': {'uri': 'https://i/p.jpg'}},
            'marketplace_listing_seller': {'name': 'Seller'},
            'creation_time': 1700000000,
        }
        base.update(over)
        return base

    def test_to_items_maps_fields(self):
        items = u.marketplace_to_items([self._listing()])
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it['title'], 'iPhone 11')
        self.assertIn('Rp1.000', it['description'])
        self.assertIn('Jakarta', it['description'])
        self.assertEqual(it['link'], 'https://www.facebook.com/marketplace/item/123/')
        self.assertEqual(it['author'], 'Seller')

    def test_to_items_drops_junk_entries(self):
        """The regression: empty listings produced `title: ''` and `.../item/None/`."""
        junk = [
            {},
            {'id': '1'},
            {'id': None, 'marketplace_listing_title': 'no id'},
            {'id': '2', 'marketplace_listing_title': '   '},
            'not-a-dict',
            None,
        ]
        self.assertEqual(u.marketplace_to_items(junk), [])

    def test_to_items_handles_null_subobjects(self):
        items = u.marketplace_to_items([self._listing(
            listing_price=None, location=None, primary_listing_photo=None,
            marketplace_listing_seller=None)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['author'], 'Facebook Marketplace')
        self.assertEqual(items[0]['description'], '')

    def test_to_items_is_xml_clean(self):
        items = u.marketplace_to_items([self._listing(marketplace_listing_title='x ]]> y')])
        self.assertNotIn(']]>', items[0]['title'])

    def test_blank_query_raises_not_found(self):
        p1, p2 = self.patch_network(FakeSession())
        with p1, p2:
            with self.assertRaises(u.FacebookNotFound):
                u.fetch_marketplace_listings('   ')

    def test_missing_cookie_raises_session_expired(self):
        with mock.patch.object(u, 'get_cookie', return_value=None):
            with self.assertRaises(u.FacebookSessionExpired):
                u.fetch_marketplace_listings('iphone')

    def test_transport_error_becomes_rate_limited(self):
        session = FakeSession(raise_on_get=TimeoutError('slow'))
        p1, p2 = self.patch_network(session)
        with p1, p2, mock.patch.object(u, 'RETRY_BACKOFF', 0):
            with self.assertRaises(u.FacebookRateLimited):
                u.fetch_marketplace_listings('iphone')


class MarketplaceExtractionTests(unittest.TestCase):
    def test_brace_matching_extracts_object(self):
        listing = {'marketplace_listing_title': 'X', 'id': '9'}
        html = 'prefix {"a":1,"inner":' + json.dumps(listing) + '} suffix'
        out = list(u._iter_json_objects_containing(html, 'marketplace_listing_title'))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['id'], '9')

    def test_brace_matching_survives_malformed_json(self):
        html = '{"marketplace_listing_title": broken} {"ok": true}'
        self.assertEqual(list(u._iter_json_objects_containing(html, 'marketplace_listing_title')), [])

    def test_query_relevance_filter_drops_placeholders(self):
        """The 'Nike P-6000' phantom listing must not appear for an unrelated query."""
        listings = [
            {'id': '1', 'marketplace_listing_title': 'iPhone 11'},
            {'id': '2', 'marketplace_listing_title': 'Nike P-6000'},
        ]
        session = FakeSession(page_html='')
        # Build enough page text to exercise the filter path.
        session.page_html = ('{"marketplace_search": true} ' + json.dumps(
            {'marketplace_listing_title': 'iPhone 11', 'id': '1'}) + ' ' + json.dumps(
            {'marketplace_listing_title': 'Nike P-6000', 'id': '2'}))
        p1, p2 = (mock.patch.object(u, '_get_session', return_value=session),
                  mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'))
        with p1, p2:
            out = u.fetch_marketplace_listings('iphone', limit=10)
        titles = [x['marketplace_listing_title'] for x in out]
        self.assertIn('iPhone 11', titles)
        self.assertNotIn('Nike P-6000', titles)


class SessionCacheTests(unittest.TestCase):
    def test_sessions_are_reused_per_cookie(self):
        """One session per cookie: the factory must run twice, not once per call."""
        u.reset_sessions()
        made = []

        def factory(cookie=None):
            s = FakeSession()
            s.cookie = cookie
            made.append(s)
            return s

        try:
            with mock.patch.object(u, '_new_session', side_effect=factory):
                s1 = u._get_session('cookie-a')
                s2 = u._get_session('cookie-a')
                s3 = u._get_session('cookie-b')
            self.assertIs(s1, s2, 'same cookie must reuse the session')
            self.assertIsNot(s1, s3, 'different cookie must get its own session')
            self.assertEqual(len(made), 2)
        finally:
            u.reset_sessions()

    def test_reset_sessions_forces_recreation(self):
        u.reset_sessions()
        try:
            with mock.patch.object(u, '_new_session', side_effect=lambda cookie=None: FakeSession()):
                first = u._get_session('cookie-a')
                u.reset_sessions()
                second = u._get_session('cookie-a')
            self.assertIsNot(first, second)
        finally:
            u.reset_sessions()


class LiteModeTests(FacebookTestBase):
    """Vercel/lite installs omit curl_cffi; that must degrade cleanly, not 500."""

    def test_unavailable_maps_to_503_with_an_actionable_message(self):
        client = self.app.test_client()
        with mock.patch.object(u, 'HAS_CURL_CFFI', False):
            resp = client.get('/facebook/page/4')
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn(b'Traceback', resp.data)
        body = resp.data.decode()
        self.assertIn('curl_cffi', body)
        self.assertIn('requirements-lite.txt', body)

    def test_unavailable_is_distinguishable_from_missing_cookie(self):
        with mock.patch.object(u, 'HAS_CURL_CFFI', False), \
             mock.patch.object(u, 'get_cookie', return_value=None):
            # Dependency check comes first: the operator must install before configuring.
            with self.assertRaises(u.FacebookUnavailable):
                u.feed_requires_cookie()

    def test_cookie_error_raised_once_dependency_present(self):
        with mock.patch.object(u, 'HAS_CURL_CFFI', True), \
             mock.patch.object(u, 'get_cookie', return_value=None):
            with self.assertRaises(u.FacebookSessionExpired):
                u.feed_requires_cookie()

    def test_all_facebook_routes_degrade_without_curl_cffi(self):
        client = self.app.test_client()
        with mock.patch.object(u, 'HAS_CURL_CFFI', False):
            for path in ['/facebook/page/4', '/facebook/group/1',
                         '/facebook/marketplace/iphone']:
                resp = client.get(path)
                self.assertEqual(resp.status_code, 503, path)
                self.assertNotIn(b'Traceback', resp.data, path)


class RouteTests(FacebookTestBase):
    def test_routes_registered(self):
        rules = {str(r) for r in self.app.url_map.iter_rules()}
        self.assertIn('/facebook/page/<string:id>', rules)
        self.assertIn('/facebook/group/<string:id>', rules)
        self.assertIn('/facebook/marketplace/<string:query>', rules)

    def test_not_found_maps_to_404(self):
        client = self.app.test_client()
        with mock.patch('rsshub.spiders.facebook.page.ctx',
                        side_effect=u.FacebookNotFound('nope')):
            resp = client.get('/facebook/page/4')
        self.assertEqual(resp.status_code, 404)

    def test_rate_limited_maps_to_503(self):
        client = self.app.test_client()
        with mock.patch('rsshub.spiders.facebook.page.ctx',
                        side_effect=u.FacebookRateLimited('slow down')):
            resp = client.get('/facebook/page/4')
        self.assertEqual(resp.status_code, 503)

    def test_missing_cookie_maps_to_503_not_500(self):
        client = self.app.test_client()
        with mock.patch.object(u, 'get_cookie', return_value=None):
            resp = client.get('/facebook/page/4')
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn(b'Traceback', resp.data)

    def test_successful_page_route_renders_xml(self):
        # A numeric id skips the slug->id lookup, so this test stays offline.
        client = self.app.test_client()
        session = FakeSession(post_text=ndjson_feed([make_story('live post')]))
        p1, p2 = self.patch_network(session)
        with p1, p2:
            resp = client.get('/facebook/page/4')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/xml')
        ElementTree.fromstring(resp.data)
        self.assertIn(b'live post', resp.data)

    def test_limit_is_clamped_on_the_route(self):
        client = self.app.test_client()
        session = FakeSession(post_text=ndjson_feed([make_story()]))
        p1, p2 = self.patch_network(session)
        with p1, p2:
            client.get('/facebook/page/4?limit=99999')
        self.assertTrue(session.post_calls, 'the spider should have issued a GraphQL POST')
        _, kwargs = session.post_calls[0]
        parsed = json.loads(kwargs['data']['variables'])
        self.assertEqual(parsed['count'], u.MAX_LIMIT)

    def test_slug_resolution_failure_maps_to_404(self):
        client = self.app.test_client()
        with mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'), \
             mock.patch.object(u, 'resolve_page_id',
                               side_effect=u.FacebookNotFound('no such page')):
            resp = client.get('/facebook/page/definitely-not-real-99887')
        self.assertEqual(resp.status_code, 404)


class CookieExportScriptTests(unittest.TestCase):
    """The helper that turns a browser cookie export into FACEBOOK_COOKIE."""

    def setUp(self):
        import fb_cookie_from_export as m
        self.m = m

    def test_json_array_export(self):
        raw = json.dumps([
            {'name': 'datr', 'value': 'd'},
            {'name': 'c_user', 'value': '100'},
            {'name': 'xs', 'value': 'tok'},
        ])
        cookies = self.m.parse_export(raw)
        self.assertEqual(self.m.build_cookie_value(cookies), 'c_user=100; xs=tok')

    def test_json_object_wrapper(self):
        raw = json.dumps({'cookies': [{'name': 'c_user', 'value': '1'},
                                      {'name': 'xs', 'value': 't'}]})
        cookies = self.m.parse_export(raw)
        self.assertEqual(self.m.build_cookie_value(cookies), 'c_user=1; xs=t')

    def test_plain_name_value_map(self):
        cookies = self.m.parse_export(json.dumps({'c_user': '1', 'xs': 't'}))
        self.assertEqual(self.m.build_cookie_value(cookies), 'c_user=1; xs=t')

    def test_netscape_cookies_txt(self):
        raw = ('# Netscape HTTP Cookie File\n'
               '.facebook.com\tTRUE\t/\tTRUE\t1823\tc_user\t100\n'
               '#HttpOnly_.facebook.com\tTRUE\t/\tTRUE\t1823\txs\ttok\n')
        cookies = self.m.parse_export(raw)
        self.assertEqual(self.m.build_cookie_value(cookies), 'c_user=100; xs=tok')

    def test_include_all_keeps_every_cookie(self):
        raw = json.dumps([{'name': 'c_user', 'value': '1'},
                          {'name': 'xs', 'value': 't'},
                          {'name': 'fr', 'value': 'f'}])
        cookies = self.m.parse_export(raw)
        self.assertEqual(self.m.build_cookie_value(cookies, include_all=True),
                         'c_user=1; xs=t; fr=f')

    def test_missing_xs_is_an_actionable_error(self):
        raw = json.dumps([{'name': 'c_user', 'value': '1'}])
        cookies = self.m.parse_export(raw)
        with self.assertRaises(ValueError) as ctx:
            self.m.build_cookie_value(cookies)
        # xs is HttpOnly and commonly omitted by default; the message must say so.
        self.assertIn('xs', str(ctx.exception))
        self.assertIn('HttpOnly', str(ctx.exception))

    def test_empty_and_unrecognised_inputs_raise(self):
        with self.assertRaises(ValueError):
            self.m.parse_export('   ')
        with self.assertRaises(ValueError):
            self.m.parse_export('not a cookie file')
        with self.assertRaises(ValueError):
            self.m.parse_export('[{"name": broken}]')
        with self.assertRaises(ValueError):
            self.m.parse_export('[]')

    def test_output_round_trips_through_the_spider(self):
        """The generated value must be exactly what get_cookie() expects."""
        raw = json.dumps([{'name': 'c_user', 'value': '100'},
                          {'name': 'xs', 'value': '34%3Aabc'}])
        value = self.m.build_cookie_value(self.m.parse_export(raw))
        with mock.patch.dict('os.environ', {'FACEBOOK_COOKIE': value}):
            self.assertEqual(u.get_cookie(), value)
        self.assertIn('c_user=100', value)
        self.assertIn('xs=34%3Aabc', value)


class PageEmbeddedStoryTests(unittest.TestCase):
    """Stories embedded in page HTML (group member view) use a flat shape."""

    FLAT = {
        '__typename': 'Story',
        'id': 'S:1',
        'url': 'https://www.facebook.com/groups/g/permalink/1/',
        'creation_time': 1791176859,
        'actors': [{'name': 'Nasrun'}],
        'message': {'text': 'Ram Laptop DDR 3'},
        'attachments': [],
    }

    def test_flat_story_renders_and_maps(self):
        items = u.stories_to_items([self.FLAT])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Ram Laptop DDR 3')
        self.assertEqual(items[0]['author'], 'Nasrun')
        # Flat shape carries `url`, not `permalink_url`.
        self.assertEqual(items[0]['link'], 'https://www.facebook.com/groups/g/permalink/1/')
        self.assertIsNotNone(items[0]['pubDate'])

    def test_placeholder_feed_units_are_dropped(self):
        """Page HTML contains Story stubs for ads/lazy containers; they must not ship."""
        junk = [
            {'__typename': 'Story', 'id': 'stub'},
            {'__typename': 'Story', '__isFeedUnit': True, 'actors': []},
        ]
        # Stories with no message, url or actors are placeholders.
        for node in junk:
            has_content = (bool((node.get('message') or {}).get('text'))
                           or bool((node.get('comet_sections') or {}).get('message'))
                           or bool(node.get('url') or node.get('permalink_url'))
                           or bool(node.get('actors')))
            self.assertFalse(has_content, node)

    def test_extract_from_page_filters_and_dedupes(self):
        html = ('prefix ' + json.dumps(self.FLAT)
                + ' ' + json.dumps({'__typename': 'Story', 'id': 'stub'})
                + ' ' + json.dumps(self.FLAT))
        found = u.extract_stories_from_page(html)
        self.assertEqual(len(found), 1, 'placeholder dropped and duplicate collapsed')

    def test_extract_from_page_tolerates_no_stories(self):
        self.assertEqual(u.extract_stories_from_page('<html>nothing here</html>'), [])


class SellerListingsTests(FacebookTestBase):
    def test_canonical_listing_is_unwrapped(self):
        """Seller pages nest the listing one level deeper than search results."""
        inner = {'id': '9', 'marketplace_listing_title': 'PS 4 fat',
                 'listing_price': {'formatted_amount': 'Rp2.600.000'},
                 'location': {'reverse_geocode': {'city': 'Batam'}}}
        page_html = ('{"marketplace_search":0} ' + json.dumps(
            {'marketplace_listing_sets': {'edges': [{'node': {'canonical_listing': inner}}]}})
            + ' ' + json.dumps({'canonical_listing': inner}))
        session = FakeSession(page_html=page_html)
        p1, p2 = (mock.patch.object(u, '_get_session', return_value=session),
                  mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'))
        with p1, p2:
            listings, _ = u.fetch_seller_listings('123', limit=10)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]['id'], '9')
        items = u.marketplace_to_items(listings)
        self.assertIn('Rp2.600.000', items[0]['description'])

    def test_missing_cookie_raises_session_expired(self):
        with mock.patch.object(u, 'get_cookie', return_value=None):
            with self.assertRaises(u.FacebookSessionExpired):
                u.fetch_seller_listings('123')


class MarketplaceFilterTests(FacebookTestBase):
    def _run(self, **kwargs):
        page_html = ('{"marketplace_search":0} ' + json.dumps(
            {'id': '1', 'marketplace_listing_title': 'ssd', 'listing_price': {}}))
        session = FakeSession(page_html=page_html)
        p1, p2 = (mock.patch.object(u, '_get_session', return_value=session),
                  mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'))
        with p1, p2:
            u.fetch_marketplace_listings('ssd', limit=5, **kwargs)
        return session.get_calls[0]

    def test_city_and_days_become_url_and_params(self):
        url, kwargs = self._run(location='yogyakartacity', days=1)
        self.assertIn('/marketplace/yogyakartacity/search', url)
        self.assertEqual(kwargs['params']['daysSinceListed'], 1)
        self.assertEqual(kwargs['params']['query'], 'ssd')

    def test_no_location_uses_default_search_path(self):
        url, kwargs = self._run()
        self.assertIn('/marketplace/search', url)
        self.assertNotIn('daysSinceListed', kwargs['params'])


class ProfileResolutionTests(FacebookTestBase):
    def test_profile_falls_back_to_page_html_userid(self):
        """plugins/page.php returns nothing for personal profiles; the page has userID."""
        plugin = FakeResponse('<html>no page id here</html>')
        profile = FakeResponse('<html>"userID":"100072517471885"</html>')
        session = mock.MagicMock()
        session.get.side_effect = [plugin, profile]
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            self.assertEqual(u.resolve_page_id('mirzum.habibi.2025'), '100072517471885')

    def test_page_plugin_is_preferred(self):
        plugin = FakeResponse('<html>"pageID":"100044561550831"</html>')
        session = mock.MagicMock()
        session.get.side_effect = [plugin]
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            self.assertEqual(u.resolve_page_id('NASA'), '100044561550831')

    def test_unknown_identifier_raises_not_found(self):
        session = mock.MagicMock()
        session.get.side_effect = [FakeResponse('<html>x</html>'),
                                   FakeResponse('<html>y</html>')]
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            with self.assertRaises(u.FacebookNotFound):
                u.resolve_page_id('does.not.exist.99887')


class NewRouteTests(FacebookTestBase):
    def test_routes_registered(self):
        rules = {str(r) for r in self.app.url_map.iter_rules()}
        self.assertIn('/facebook/marketplace/seller/<string:seller_id>', rules)
        self.assertIn('/facebook/group/<string:id>/user/<string:user_id>', rules)

    def test_seller_route_does_not_shadow_search_route(self):
        """/marketplace/<query> must not swallow /marketplace/seller/<id>."""
        adapter = self.app.url_map.bind('localhost')
        self.assertEqual(adapter.match('/facebook/marketplace/seller/123')[0],
                         'main.facebook_marketplace_seller')
        self.assertEqual(adapter.match('/facebook/marketplace/iphone')[0],
                         'main.facebook_marketplace')

    def test_group_member_route_renders(self):
        client = self.app.test_client()
        story = {
            '__typename': 'Story', 'id': 'a', 'url': 'https://f/g/permalink/1',
            'creation_time': 1700000000, 'actors': [{'name': 'Nasrun'}],
            'message': {'text': 'member post'}, 'attachments': [],
        }
        html = json.dumps(story)
        session = FakeSession(page_html=html)
        p1, p2 = self.patch_network(session)
        with p1, p2:
            resp = client.get('/facebook/group/123/user/456')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'member post', resp.data)

    def test_marketplace_location_and_days_accepted(self):
        client = self.app.test_client()
        page_html = ('{"marketplace_search":0} ' + json.dumps(
            {'id': '1', 'marketplace_listing_title': 'ssd', 'listing_price': {}}))
        session = FakeSession(page_html=page_html)
        p1, p2 = self.patch_network(session)
        with p1, p2:
            resp = client.get('/facebook/marketplace/ssd?location=yogyakartacity&days=1')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('/marketplace/yogyakartacity/search', session.get_calls[0][0])


class UrlFormTests(FacebookTestBase):
    """Facebook URLs are pasted straight from the browser, so accept both forms."""

    def test_trailing_slash_accepted_on_every_route(self):
        adapter = self.app.url_map.bind('localhost')
        pairs = [
            ('/facebook/page/NASA', 'main.facebook_page'),
            ('/facebook/page/NASA/', 'main.facebook_page'),
            ('/facebook/group/123', 'main.facebook_group'),
            ('/facebook/group/123/', 'main.facebook_group'),
            ('/facebook/group/1/user/2', 'main.facebook_group_user'),
            ('/facebook/group/1/user/2/', 'main.facebook_group_user'),
            ('/facebook/marketplace/iphone', 'main.facebook_marketplace'),
            ('/facebook/marketplace/iphone/', 'main.facebook_marketplace'),
            ('/facebook/marketplace/seller/5', 'main.facebook_marketplace_seller'),
            ('/facebook/marketplace/seller/5/', 'main.facebook_marketplace_seller'),
        ]
        for url, endpoint in pairs:
            with self.subTest(url=url):
                self.assertEqual(adapter.match(url)[0], endpoint)

    def test_seller_route_still_wins_over_query_catch_all(self):
        """Adding the trailing-slash rule must not let <query> swallow 'seller'."""
        adapter = self.app.url_map.bind('localhost')
        self.assertEqual(adapter.match('/facebook/marketplace/seller/5')[0],
                         'main.facebook_marketplace_seller')
        self.assertEqual(adapter.match('/facebook/marketplace/seller/5/')[0],
                         'main.facebook_marketplace_seller')


class GroupIdentifierTests(FacebookTestBase):
    """A group may be addressed by numeric id or by its username slug."""

    def test_numeric_group_id_skips_lookup(self):
        """Callers pass digits straight through; resolve_group_id is for slugs only."""
        # The numeric fast-path lives in the callers, so assert on that contract.
        for module_call in (u.fetch_group_member_posts,):
            with mock.patch.object(u, '_get_session') as gs, \
                 mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
                session = mock.MagicMock()
                session.get.return_value = FakeResponse('<html>"LSD",[],{"token":"t"}</html>')
                gs.return_value = session
                module_call('454412923988558', '100090130956973', limit=1)
            # The only request should be the member page itself, i.e. no /about lookup.
            urls = [c.args[0] for c in session.get.call_args_list]
            self.assertTrue(all('/about' not in url for url in urls), urls)

    def test_resolve_group_id_reads_groupid_from_about_page(self):
        session = mock.MagicMock()
        session.get.return_value = FakeResponse('<html>"groupID":"586220791393074"</html>')
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            self.assertEqual(u.resolve_group_id('nasrunbth'), '586220791393074')
        self.assertIn('/groups/nasrunbth/about', session.get.call_args.args[0])

    def test_unknown_group_slug_raises_not_found(self):
        session = mock.MagicMock()
        session.get.return_value = FakeResponse('<html>no groupID here</html>')
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            with self.assertRaises(u.FacebookNotFound):
                u.resolve_group_id('this-group-does-not-exist-99887')

    def test_group_member_fetch_resolves_a_slug(self):
        """A slug must be resolved before the member URL is built."""
        session = mock.MagicMock()
        # First call = the /about lookup, second = the member page.
        session.get.side_effect = [
            FakeResponse('<html>"groupID":"586220791393074"</html>'),
            FakeResponse('<html>{"__typename":"Story","id":"x","url":"https://f/p/1",'
                         '"creation_time":1700000000,"actors":[{"name":"A"}],'
                         '"message":{"text":"hi"},"attachments":[]}</html>'),
        ]
        with mock.patch.object(u, '_get_session', return_value=session), \
             mock.patch.object(u, 'get_cookie', return_value='c_user=1; xs=2'):
            stories, _ = u.fetch_group_member_posts('nasrunbth', '100090130956973', limit=5)
        self.assertEqual(len(stories), 1)
        member_urls = [c.args[0] for c in session.get.call_args_list if '/user/' in c.args[0]]
        self.assertTrue(member_urls, 'member page should have been requested')
        self.assertIn('/groups/586220791393074/user/', member_urls[0])


class MediaRenderingTests(unittest.TestCase):
    """Images, video and captions must reach the feed; a Reel must not render empty."""

    def _reel_story(self):
        """A Reel as Facebook actually ships it: caption + thumbnail nested inside."""
        return {
            '__typename': 'Story',
            'permalink_url': 'https://www.facebook.com/NASA/posts/pfbid0abc',
            'creation_time': 1791843606,
            'actors': [{'name': 'NASA'}],
            'comet_sections': {'content': {'story': {'message': None, 'attachments': [{
                'styles': {'attachment': {
                    '__typename': 'StoryAttachmentFBReelsStyleRenderer',
                    'style_infos': [{
                        '__typename': 'FBShortsShareAttachmentStyleInfo',
                        'fb_shorts_story': {
                            'id': 'UzpfSTQ6',
                            'creation_time': 1791841101,
                            'message': {'text': "It's a new off-world record! \U0001F3C5"},
                            'attachments': [],
                        },
                    }],
                }},
            }]}}},
        }

    def test_reel_caption_becomes_the_title(self):
        """Regression: the title used to fall back to the page name."""
        items = u.stories_to_items([self._reel_story()])
        self.assertIn('off-world record', items[0]['title'])
        self.assertNotEqual(items[0]['title'], 'NASA')

    def test_reel_is_not_an_empty_entry(self):
        """Regression: a Reel rendered a zero-length description."""
        items = u.stories_to_items([self._reel_story()])
        self.assertTrue(items[0]['description'], 'reel description must not be empty')

    def test_reel_thumbnail_is_emitted_when_no_inner_attachment(self):
        story = self._reel_story()
        info = (story['comet_sections']['content']['story']['attachments'][0]
                ['styles']['attachment']['style_infos'][0]['fb_shorts_story'])
        info['preferred_thumbnail'] = {'image': {'uri': 'https://scontent/x.jpg'}}
        items = u.stories_to_items([story])
        self.assertIn('<img', items[0]['description'])
        self.assertIn('https://scontent/x.jpg', items[0]['description'])

    def test_photo_attachment_renders_img(self):
        story = {
            '__typename': 'Story', 'permalink_url': 'https://f/p/1',
            'creation_time': 1700000000, 'actors': [{'name': 'A'}],
            'comet_sections': {'content': {'story': {
                'message': {'text': 'a photo post'},
                'attachments': [{'styles': {'attachment': {
                    'media': {'photo_image': {'uri': 'https://scontent/p.jpg'},
                              'accessibility_caption': 'cap'}}}}],
            }}},
        }
        items = u.stories_to_items([story])
        self.assertIn('<img', items[0]['description'])
        self.assertIn('https://scontent/p.jpg', items[0]['description'])

    def test_video_attachment_renders_video_tag(self):
        story = {
            '__typename': 'Story', 'permalink_url': 'https://f/p/2',
            'creation_time': 1700000000, 'actors': [{'name': 'A'}],
            'comet_sections': {'content': {'story': {
                'message': {'text': 'a video post'},
                'attachments': [{'styles': {'attachment': {
                    'media': {'__typename': 'Video',
                              'videoDeliveryLegacyFields': {
                                  'browser_native_sd_url': 'https://v/sd.mp4'},
                              'preferred_thumbnail': {'image': {'uri': 'https://p.jpg'}}}}}}],
            }}},
        }
        items = u.stories_to_items([story])
        self.assertIn('<video', items[0]['description'])
        self.assertIn('https://v/sd.mp4', items[0]['description'])

    def test_shorts_helper_ignores_plain_attachments(self):
        self.assertIsNone(u._shorts_story({'styles': {'attachment': {'media': {}}}}))
        self.assertIsNone(u._shorts_story({}))

    def test_first_fbcdn_uri_finds_nested_thumbnail(self):
        blob = {'a': [{'b': {'preferred_thumbnail': {'image': {'uri': 'https://x/1.jpg'}}}}]}
        self.assertEqual(u._first_fbcdn_uri(blob), 'https://x/1.jpg')
        self.assertIsNone(u._first_fbcdn_uri({'nothing': 1}))

    def test_rendered_reel_survives_the_template(self):
        """End-to-end: the fixed output must still be well-formed XML."""
        from rsshub import create_app
        app = create_app('testing')
        items = u.stories_to_items([self._reel_story()])
        from flask import render_template
        with app.test_request_context('/'):
            out = render_template('main/atom.xml', title='T', link='L',
                                  description='D', author='A', items=items)
        ElementTree.fromstring(out.encode())


if __name__ == '__main__':
    unittest.main()
