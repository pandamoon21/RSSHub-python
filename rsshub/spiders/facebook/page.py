"""Facebook page / profile feed.

Port of RSSHub's lib/routes/facebook/page.ts. Works for public pages and public personal
profiles; posts sitting behind a login wall need FACEBOOK_COOKIE to be set.
"""
from rsshub.spiders.facebook.utils import (
    BASE_URL,
    DOC_IDS,
    FRIENDLY_NAMES,
    fetch_stories,
    get_route_limit,
    resolve_page_id,
    stories_to_items,
)


def ctx(id='', limit=None):
    """Return the feed dict for /facebook/page/:id."""
    page_id = id if id.isdigit() else resolve_page_id(id)
    count = get_route_limit(limit)

    stories = fetch_stories(
        FRIENDLY_NAMES['page'],
        DOC_IDS['page'],
        {
            'id': page_id,
            'feedLocation': 'TIMELINE',
            'feedbackSource': 0,
            'omitPinnedPost': True,
            'privacySelectorRenderLocation': 'COMET_STREAM',
            'renderLocation': 'timeline',
            'run_with_continuation_key': False,
            'stream_count': 1,
        },
        count,
        page_url=f'{BASE_URL}/{id}',
    )

    actor = {}
    if stories:
        story = (stories[0].get('comet_sections') or {}).get('content', {}).get('story') or {}
        actors = story.get('actors') or []
        if actors:
            actor = actors[0]

    return {
        'title': actor.get('name') or f'Facebook Page {id}',
        'link': actor.get('url') or f'{BASE_URL}/{id}',
        'description': f'Facebook posts from {actor.get("name") or id}',
        'author': actor.get('name') or id,
        'items': stories_to_items(stories),
    }
