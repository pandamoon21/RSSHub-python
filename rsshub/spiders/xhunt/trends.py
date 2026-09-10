import requests
from bs4 import BeautifulSoup
import arrow

domain = 'https://trends.xhunt.ai'

# Default headers for requests
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Try to import from rsshub.utils if available (when running in the app)
try:
    from rsshub.utils import DEFAULT_HEADERS
except ImportError:
    pass  # Use the default headers defined above


def parse_tweet(item):
    """Parse a single tweet item from the HTML"""
    result = {}
    
    # Get the link
    link_elem = item.find('a', href=True)
    if link_elem:
        result['link'] = link_elem['href']
    else:
        result['link'] = domain
    
    # Get rank
    rank_elem = item.find('span', attrs={'aria-label': lambda x: x and 'Rank' in x})
    if rank_elem:
        rank = rank_elem.get_text(strip=True)
    else:
        # Try to find any number in a badge-like element
        rank_elem = item.find('span', class_=lambda x: x and any(c in str(x) for c in ['rounded', 'bg-gradient']))
        rank = rank_elem.get_text(strip=True) if rank_elem else ''
    
    # Get author name
    author_elem = item.find('p', class_=lambda x: x and 'font-semibold' in str(x))
    author = author_elem.get_text(strip=True) if author_elem else 'Unknown'
    
    # Get author handle
    handle_elem = item.find('p', class_=lambda x: x and 'text-xs' in str(x) and 'truncate' in str(x))
    handle = handle_elem.get_text(strip=True) if handle_elem else ''
    
    # Get tweet content
    content_elem = item.find('p', class_=lambda x: x and 'mt-0.5' in str(x) and 'truncate' in str(x))
    content = content_elem.get_text(strip=True) if content_elem else ''
    
    # Get metrics (views, likes, retweets)
    metrics = item.find_all('span', title=True)
    views = ''
    likes = ''
    retweets = ''
    for metric in metrics:
        title = metric.get('title', '')
        text = metric.get_text(strip=True)
        if 'Views' in title or '浏览' in title:
            views = text
        elif 'Likes' in title or '点赞' in title:
            likes = text
        elif 'Retweets' in title or '转发' in title:
            retweets = text
    
    # Get heat score
    heat_elem = item.find('span', title=lambda x: x and ('热度' in str(x) or 'heat' in str(x).lower()))
    heat = ''
    if heat_elem:
        heat_span = heat_elem.find('span')
        if heat_span:
            heat = heat_span.get_text(strip=True)
    
    # Build title and description
    result['title'] = f"[{rank}] {author} {handle}: {content[:80]}{'...' if len(content) > 80 else ''}"
    
    description_parts = []
    if content:
        description_parts.append(f"<p>{content}</p>")
    if views or likes or retweets:
        metrics_str = f"Views: {views} | Likes: {likes} | Retweets: {retweets}"
        description_parts.append(f"<p>{metrics_str}</p>")
    if heat:
        description_parts.append(f"<p>Heat Score: {heat}</p>")
    
    result['description'] = ''.join(description_parts) if description_parts else content
    result['author'] = f"{author} {handle}".strip()
    result['pubDate'] = arrow.now().isoformat()
    
    return result


def ctx(group='global', hours='24', tag='ai'):
    """Main function to fetch xhunt trends"""
    url = f'{domain}/zh/tweets?group={group}&hours={hours}&tag={tag}'
    
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find the list container
        list_container = soup.find('ul', attrs={'role': 'list'})
        
        items = []
        if list_container:
            # Find all list items
            tweet_items = list_container.find_all('li')
            for item in tweet_items:
                try:
                    parsed = parse_tweet(item)
                    if parsed.get('title'):
                        items.append(parsed)
                except Exception as e:
                    # Skip items that fail to parse
                    continue
        
        # Get tag name for title
        tag_display = tag.upper() if tag else 'Trends'
        group_display = 'Global' if group == 'global' else 'Chinese'
        
        return {
            'title': f'XHunt {group_display} {tag_display} Trends - {hours}h',
            'link': url,
            'description': f'XHunt AI trending tweets - Group: {group}, Tag: {tag}, Hours: {hours}',
            'author': 'xhunt',
            'items': items
        }
        
    except Exception as e:
        return {
            'title': f'XHunt Trends - Error',
            'link': url,
            'description': f'Failed to fetch data: {str(e)}',
            'author': 'xhunt',
            'items': []
        }
