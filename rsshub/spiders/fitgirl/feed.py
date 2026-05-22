import re
import requests
from bs4 import BeautifulSoup
from rsshub.utils import DEFAULT_HEADERS

def clean_fitgirl_html(html_content, original_link):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    cover_img = soup.find('img', class_='alignleft')
    img_url = cover_img['src'] if cover_img else ''
    
    info_p = soup.find(lambda tag: tag.name == 'p' and 'Genres/Tags:' in tag.text)
    if info_p:
        for img in info_p.find_all('img'):
            img.decompose()
        for a in info_p.find_all('a'):
            a.unwrap()
    info_text = info_p.get_text(separator='<br>').strip() if info_p else ''
    info_text = re.sub(r'(<br>\s*)+', '<br>', info_text).strip('<br>')
    
    download_links = []
    
    h3_direct = soup.find(lambda tag: tag.name == 'h3' and 'Direct' in tag.text)
    if h3_direct:
        ul = h3_direct.find_next_sibling('ul')
        if ul:
            for li in ul.find_all('li'):
                a = li.find('a')
                if a and a.has_attr('href'):
                    name = a.text.replace('Filehoster:', '').strip()
                    download_links.append(f"<a href='{a['href']}'>{name}</a>")
                    
    h3_torrent = soup.find(lambda tag: tag.name == 'h3' and 'Torrent' in tag.text)
    if h3_torrent:
        ul = h3_torrent.find_next_sibling('ul')
        if ul:
            for li in ul.find_all('li'):
                a = li.find('a')
                if a and a.has_attr('href'):
                    download_links.append(f"<a href='{a['href']}'>{a.text}</a>")
                magnet = li.find('a', href=lambda href: href and href.startswith('magnet:'))
                if magnet:
                    download_links.append(f"<a href='{magnet['href']}'>Magnet</a>")
                    
    desc_div = soup.find('div', class_='su-spoiler-content')
    game_desc = desc_div.get_text(separator='<br>').strip() if desc_div else ''
    game_desc = re.sub(r'(<br>\s*)+', '<br>', game_desc).strip('<br>')
    
    clean_html = ""
    if img_url:
        clean_html += f"<img referrerpolicy='no-referrer' src='{img_url}'><br><br>"
    if info_text:
        clean_html += f"<b>Game Info:</b><br>{info_text}<br><br>"
    if download_links:
        clean_html += "<b>Download Links:</b><br>" + " | ".join(download_links) + "<br><br>"
    if game_desc:
        clean_html += f"<b>Description:</b><br>{game_desc}<br><br>"
        
    clean_html += f"<a href='{original_link}'>View on FitGirl Repacks</a>"
    return clean_html

def parse(item):
    title = item.find('title')
    link = item.find('link')
    description = item.find('description')
    pubDate = item.find('pubDate')
    creator = item.find('dc:creator') or item.find('creator')

    content_encoded = item.find('encoded')
    desc_text = content_encoded.text if content_encoded else (description.text if description else '')
    
    original_link = link.text if link else ''
    cleaned_desc = clean_fitgirl_html(desc_text, original_link)

    return {
        'title': title.text if title else '',
        'link': original_link,
        'description': cleaned_desc,
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
