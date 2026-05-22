import requests
from bs4 import BeautifulSoup
from rsshub.utils import DEFAULT_HEADERS

def parse(item):
    title = item.find('title')
    link = item.find('link')
    description = item.find('description')
    pubDate = item.find('pubDate')
    creator = item.find('dc:creator') or item.find('creator')

    # Fitgirl's description might have some embedded images or HTML, we keep it as is
    # The 'encoded' content namespace is usually used for full HTML body in WP RSS,
    # let's try to get content:encoded if available, else fallback to description.
    content_encoded = item.find('encoded')
    desc_text = content_encoded.text if content_encoded else (description.text if description else '')

    return {
        'title': title.text if title else '',
        'link': link.text if link else '',
        'description': desc_text,
        'pubDate': pubDate.text if pubDate else '',
        'author': creator.text if creator else 'FitGirl'
    }

def ctx():
    url = 'https://fitgirl-repacks.site/feed/'
    headers = dict(DEFAULT_HEADERS)
    headers['Referer'] = 'https://fitgirl-repacks.site/'

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'xml')
        items_tags = soup.find_all('item')
        items = [parse(item) for item in items_tags]
    except Exception as e:
        print(f"[FitGirl] Error fetching feed: {e}")
        items = []

    return {
        'title': 'FitGirl Repacks',
        'link': 'https://fitgirl-repacks.site/',
        'description': 'The ONLY official site for FitGirl Repacks.',
        'author': 'FitGirl',
        'items': items
    }
