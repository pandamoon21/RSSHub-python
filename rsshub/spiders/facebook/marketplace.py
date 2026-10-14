"""Facebook Marketplace search feed.

Unlike the page/group routes this is not a port of an upstream RSSHub route — RSSHub has
never implemented Marketplace. Listings are embedded in the search page as nested JSON, so
this scrapes that rather than calling a GraphQL doc_id (Marketplace's doc_ids are loaded
from JS bundles and are not stable).

Requires FACEBOOK_COOKIE: Marketplace is login-walled, and results are location-scoped to
the account's own Marketplace region.
"""
from rsshub.spiders.facebook.utils import (
    BASE_URL,
    fetch_marketplace_listings,
    get_route_limit,
    marketplace_to_items,
)


def ctx(query='', limit=None):
    """Return the feed dict for /facebook/marketplace/:query."""
    count = get_route_limit(limit)
    query = (query or '').strip()

    listings = fetch_marketplace_listings(query, limit=count)
    items = marketplace_to_items(listings)

    return {
        'title': f'Facebook Marketplace: {query}',
        'link': f'{BASE_URL}/marketplace/search/?query={query}',
        'description': f'Facebook Marketplace listings matching "{query}"',
        'author': 'Facebook Marketplace',
        'items': items,
    }
