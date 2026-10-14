"""Facebook group feed.

Port of RSSHub's lib/routes/facebook/group.ts. Posts are pulled chronologically; a
login-walled group needs FACEBOOK_COOKIE to be set.
"""
from rsshub.spiders.facebook.utils import (
    BASE_URL,
    DOC_IDS,
    FRIENDLY_NAMES,
    fetch_stories,
    get_route_limit,
    resolve_group_id,
    stories_to_items,
)


def ctx(id='', limit=None):
    """Return the feed dict for /facebook/group/:id."""
    group_id = id if id.isdigit() else resolve_group_id(id)
    count = get_route_limit(limit)

    stories = fetch_stories(
        FRIENDLY_NAMES['group'],
        DOC_IDS['group'],
        {
            'id': group_id,
            'feedLocation': 'GROUP',
            'feedType': 'DISCUSSION',
            'feedbackSource': 0,
            'privacySelectorRenderLocation': 'COMET_STREAM',
            'renderLocation': 'group',
            'sortingSetting': 'CHRONOLOGICAL',
            'stream_initial_count': 1,
            'youthIntegrityHostID': group_id,
        },
        count,
        page_url=f'{BASE_URL}/groups/{id}',
    )

    # The group object is reachable from the first story's "to" field.
    group = (stories[0].get('to') if stories else None) or {}

    return {
        'title': group.get('name') or f'Facebook Group {id}',
        'link': group.get('url') or f'{BASE_URL}/groups/{id}',
        'description': f'Facebook group posts from {group.get("name") or id}',
        'author': group.get('name') or id,
        'items': stories_to_items(stories),
    }
