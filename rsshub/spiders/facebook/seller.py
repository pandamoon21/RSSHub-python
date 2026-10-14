"""Facebook Marketplace seller listings.

Turns a seller profile URL like
``facebook.com/marketplace/profile/<seller_id>/`` into a feed of that seller's active
listings. Not a port of upstream RSSHub — it has no Marketplace route.

Seller pages differ structurally from search results: each item is nested under
``marketplace_listing_sets.edges[].node.canonical_listing`` rather than sitting at the
top level, which fetch_seller_listings unwraps.
"""
from rsshub.spiders.facebook.utils import (
    BASE_URL,
    fetch_seller_listings,
    get_route_limit,
    marketplace_to_items,
)


def ctx(seller_id='', limit=None):
    """Return the feed dict for /facebook/marketplace/seller/:seller_id."""
    count = get_route_limit(limit)

    listings, seller_name = fetch_seller_listings(seller_id, limit=count)
    items = marketplace_to_items(listings)

    name = seller_name or seller_id
    return {
        'title': f'Facebook Marketplace: {name}',
        'link': f'{BASE_URL}/marketplace/profile/{seller_id}/',
        'description': f'Marketplace listings from {name}',
        'author': name,
        'items': items,
    }
