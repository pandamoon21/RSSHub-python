import asyncio
import re
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from rsshub.utils import DEFAULT_HEADERS


def extract_author(title):
    """Extract author/release group from title (e.g., 'Game Name-GOG' -> 'GOG')"""
    if '-' in title:
        parts = title.rsplit('-', 1)
        if len(parts) == 2:
            return parts[1].strip()
    return 'OvaGames'


async def fetch_page(session, url):
    """Fetch a single page asynchronously"""
    response = await session.get(url)
    return response.text


async def fetch_game_details(session, url):
    """Fetch and parse game details from individual game page"""
    try:
        html = await fetch_page(session, url)
        soup = BeautifulSoup(html, 'html.parser')

        details = {}
        post_wrapper = soup.select_one('.post-wrapper')
        if not post_wrapper:
            return None

        # Get cover image
        cover_img = post_wrapper.select_one('p > img.aligncenter')
        if cover_img:
            details['cover_image'] = cover_img.get('src', '')

        # Find the paragraph with game info (contains Title, Genre, etc.)
        for p in post_wrapper.select('p'):
            text = p.get_text()
            if 'Title:' in text and 'Genre:' in text:
                html_str = str(p)

                field_patterns = {
                    'title': r'<strong>Title</strong></span>:\s*([^<]+)',
                    'genre': r'<strong>Genre</strong></span>:\s*([^<]+)',
                    'developer': r'<strong>Developer</strong></span>:\s*([^<]+)',
                    'publisher': r'<strong>Publisher</strong></span>:\s*([^<]+)',
                    'release_date': r'<strong>Release Date</strong></span>:\s*([^<]+)',
                    'languages': r'<strong>Languages</strong></span>:\s*([^<]+)',
                    'file_size': r'<strong>File Size</strong></span>:\s*([^<]+)',
                }

                for key, pattern in field_patterns.items():
                    match = re.search(pattern, html_str, re.IGNORECASE)
                    if match:
                        details[key] = match.group(1).strip()
                break

        # Get mirrors from download tab
        mirrors = []
        tabs_container = post_wrapper.select_one('#wp-tabs-1, .wp-tabs')
        if tabs_container:
            tab_titles = tabs_container.select('h3.wp-tab-title')
            tab_contents = tabs_container.select('div.wp-tab-content')

            for i, title in enumerate(tab_titles):
                title_text = title.get_text().upper()
                if i < len(tab_contents):
                    content = tab_contents[i]

                    # LINK DOWNLOAD tab - get mirrors
                    if 'DOWNLOAD' in title_text:
                        for link in content.select('a[href*="filecrypt"]'):
                            mirror_name = link.get_text(strip=True)
                            mirror_url = link.get('href', '')
                            if mirror_name and mirror_url:
                                mirrors.append({'name': mirror_name, 'url': mirror_url})

                    # INSTALL NOTE tab
                    elif 'INSTALL' in title_text:
                        wrapper = content.select_one('.wp-tab-content-wrapper')
                        if wrapper:
                            details['install_notes'] = wrapper.get_text(separator='\n').strip()

        details['mirrors'] = mirrors
        return details

    except Exception as e:
        return None


def build_description(details, link, imgurl):
    """Build the description HTML from game details"""
    parts = []

    if imgurl:
        parts.append(f"<img referrerpolicy='no-referrer' src='{imgurl}'>")

    if details:
        info_lines = []
        fields = [
            ('title', 'Title'),
            ('genre', 'Genre'),
            ('developer', 'Developer'),
            ('publisher', 'Publisher'),
            ('release_date', 'Release Date'),
            ('languages', 'Languages'),
            ('file_size', 'File Size')
        ]

        for key, label in fields:
            if details.get(key):
                info_lines.append(f"<b>{label}:</b> {details[key]}")

        if info_lines:
            parts.append("<br>".join(info_lines))

        # Mirrors with hyperlinks
        if details.get('mirrors'):
            mirror_links = [f"<a href='{m['url']}'>{m['name']}</a>" for m in details['mirrors']]
            parts.append(f"<b>Mirrors:</b> {' | '.join(mirror_links)}")

        # Install notes
        if details.get('install_notes'):
            install_html = details['install_notes'].replace('\n', '<br>').replace('<br><br>', '<br>')
            parts.append(f"<b>Install Notes:</b><br>{install_html}")

    parts.append(f"<a href='{link}'>View on OvaGames</a>")

    return "<br><br>".join(parts)


async def parse_with_details(session, post):
    """Parse a single post and fetch its details asynchronously"""
    item = {}

    title_elem = post.select_one('.home-post-titles h2 a')
    if title_elem:
        full_title = title_elem.get('title', '')
        item['title'] = full_title.replace('Permanent Link to ', '')
        item['link'] = title_elem.get('href', '')
    else:
        item['title'] = 'Unknown'
        item['link'] = ''

    item['author'] = extract_author(item['title'])

    img_elem = post.select_one('.post-inside img.thumbnail')
    imgurl = img_elem.get('src', '') if img_elem else ''

    details = None
    if item['link']:
        details = await fetch_game_details(session, item['link'])

    if details and details.get('cover_image'):
        imgurl = details['cover_image']

    item['description'] = build_description(details, item['link'], imgurl)
    item['pubDate'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return item


async def ctx_async():
    """Async main function to fetch and parse ovagames.com"""
    headers = dict(DEFAULT_HEADERS)
    headers['Referer'] = 'https://www.ovagames.com'

    url = 'https://www.ovagames.com'

    async with AsyncSession(
        headers=headers,
        impersonate="chrome",
        timeout=30
    ) as session:
        html = await fetch_page(session, url)
        soup = BeautifulSoup(html, 'html.parser')
        posts = soup.select('div.home-post-wrap')

        tasks = [parse_with_details(session, post) for post in posts]
        items = await asyncio.gather(*tasks)

    return {
        'title': 'OvaGames - New PC Games',
        'link': 'https://www.ovagames.com',
        'description': 'Download PC Games Free Full Version - OvaGames',
        'author': 'OvaGames',
        'items': items
    }


def ctx():
    """Synchronous wrapper for async ctx"""
    return asyncio.run(ctx_async())