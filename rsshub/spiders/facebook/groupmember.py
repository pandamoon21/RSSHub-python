"""Posts by one member inside a Facebook group.

Turns a URL like ``facebook.com/groups/<group_id>/user/<user_id>/`` into a feed of that
member's posts in the group. Not a port of upstream RSSHub.

Unlike the group and page feeds, this view is rendered server-side: the stories are in
the page HTML rather than behind a stable GraphQL doc_id, and their shape is flat
(``message``/``attachments``/``url``) instead of nested under ``comet_sections``.
extract_stories_from_page handles both the extraction and the shape.

Requires FACEBOOK_COOKIE. The account must already be able to see the group: private
groups will return whatever that account is permitted to read, and nothing otherwise.
"""
from rsshub.spiders.facebook.utils import (
    BASE_URL,
    fetch_group_member_posts,
    get_route_limit,
    stories_to_items,
)


def ctx(id='', user_id='', limit=None):
    """Return the feed dict for /facebook/group/:id/user/:user_id."""
    count = get_route_limit(limit)

    stories, _ = fetch_group_member_posts(id, user_id, limit=count)
    items = stories_to_items(stories)

    # The actor is on each story; use it for the feed author when available.
    author = items[0]['author'] if items and items[0]['author'] else user_id

    return {
        'title': f'Facebook Group {id}: posts by {author}',
        'link': f'{BASE_URL}/groups/{id}/user/{user_id}/',
        'description': f'Posts by {author} in Facebook group {id}',
        'author': author,
        'items': items,
    }
