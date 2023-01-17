import requests
import time
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

def get_date(rls_date):
    # 28-06-2022
    date = "{}-{}-{} 00:00:01".format(
        rls_date[-4:], rls_date[3:5], rls_date[:2]
    )
    return date

def parse(post):
    item = {}
    title_type = "movie" if post['is_movie'] == 1 else "series"
    judul = post['series_name'] if title_type == "series" else post['title']
    episode = post.get('number', None)
    totaleps = post.get('released_product_total')
    if episode:
        judul += f" E{int(episode):02}"
    category = post.get('category_name')
    judul += f" - {title_type.upper()}"
    synopsis = post.get('synopsis')
    item['title'] = judul
    imgurl1 = post['cover_image_url']
    imgurl2 = post['series_image_url']
    link_path = "{}/{}".format(
        post['id'],
        post['series_name'].replace(" ", "-").replace("(", "").replace(")", "").strip()
    )
    link = f"https://www.viu.com/ott/sg/en-us/vod/{link_path}"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}".format(
        a=f"Category: {category} - Synopsis: {synopsis} - Total Eps: {totaleps}",
        b=f"<a href='{link}'>Link contents</a>",
        c=f"<img referrerpolicy='no-referrer' src='{imgurl2}'>",
        d=f"<img referrerpolicy='no-referrer' src='{imgurl1}'>"
    )
    item['link'] = link
    # item['pubDate'] = datetime.fromtimestamp(int(time.time()) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return item

def parse2(post):
    item = {}
    print(post)
    judul = post.get('title', post.get('moviealbumshowname', post.get('display_title')))
    if not judul:
        judul = post.get('slug', '').replace('_', ' ').title()
    title_type = post.get('contenttype', post.get('genrename'))
    if title_type:
        judul += f" - {title_type.upper()}"
    episode = post.get('episodeno')
    if episode:
        judul += f" E{int(episode):02}"
    year = post.get('year_of_release')
    if year:
        judul += f" - {year}"
    category = post.get('genrename')
    synopsis = post.get('description', '')
    item['title'] = judul
    imgurl_path = post.get('tcid_16x9_t', post.get('poster_cid', post.get('tcid_16x9_t', '')))
    # set quality to low to save bandwidth
    imgurl = f"https://vuclipi-a.akamaihd.net/p/cloudinary/c_thumb,q_auto:low/{imgurl_path}"
    # https://www.viu.com/ott/id/id/all/video-bahasa_indonesia-drama-tv_shows-bad_boys_vs_crazy_girls_episode_4-1166064914
    # https://www.viu.com/ott/id/id/all/video-korean-drama-tv_shows-summer_strike_episode_12-1166081446
    # https://www.viu.com/ott/id/id/all/playlist-encyclopedia_of_useless_facts_on_unbelievable_human_beings-playlist-26273514
    # bad_boys_vs_crazy_girls_episode_4
    link_path = '{}-{}-{}-{}-{}'.format(
        post.get('slugLanguage', post.get('language', '')).lower().replace(" ", "_"),
        post['subgenrename'].lower().replace(" ", "_"),
        post['genrename'].lower().replace(" ", "_"),
        post['slug'],
        post['id']
    )
    link = f"https://www.viu.com/ott/id/id/all/video-{link_path}"
    subs = post.get("availablesubs", "").replace(",", ", ")
    ctr = post.get('country_origin', 'N/A')
    rating = post.get('display_age_rating', 'N/A')
    broad = post.get('broadcaster', post.get('contentprovider', post.get('CP_name', '')))
    item['description'] = "{}<br>{}<br>{}<br>{}<br>{}<br>{}<br>{}".format(
        f"Category: {category} - Lang: {post['language']} - Country: {ctr}",
        f"Genre: {post['subgenrename']} - Rating: {rating} - Broadcaster: {broad}",
        f"Subtitles available: {subs}",
        f"<a href='{link}'>Link contents</a>",
        synopsis,
        f"<img referrerpolicy='no-referrer' src='{imgurl}'>",
        f"tags: {post['tags'].replace(',', ' ,') if post.get('tags') else '-'}"
    )
    item['link'] = link
    start_date = post.get('start_date') # 28-06-2022
    exec_date = post.get('execution_date')
    if exec_date:
        item['pubDate'] = get_date(exec_date)
    elif start_date:
        item['pubDate'] = get_date(start_date)
            
    return item


def ctx(region=''):
    DEFAULT_HEADERS.update({
        "Origin": "https://viu.com",
        "Referer": "https://viu.com/",
    })
    if region.lower() == "sg":
        url = 'https://www.viu.com/ott/sg/index.php'
        posts = requests.get(
            url=url,
            headers={
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'x-forwarded-for': '193.56.255.18'  #  bypass SG ip restriction
            },
            params={
                "r": "listing/ajax",
                "platform_flag_label": "web",
                "area_id": "2",
                "language_flag_id": "3",
                "cpreference_id": "",
                "grid_id": "202013"
            }
        )
        posts = posts.json()['data']['series']
    elif region.lower() == "id":
        url = "https://static.viu.com/program/prod/e374a1881c6391a091b5fb586b7ec490/1672054435336/id/default/id/home.json"
        url = "https://static.viu.com/program/prod/b7a7c2fcd875bc989b92ce6e13faf8d1/1672126541858/id/default/id/home.json"
        # cari cara ambil url home.json otomatis
        res = requests.get(
            url=url,
            headers=DEFAULT_HEADERS
        )
        data = res.json()['container']
        posts = []
        posts_mov = next((x['item'] for x in data if x['slug'] == "fresh_on_viu_this_week"), [])
        posts.extend(posts_mov)
        slug_tv = [
            'sunday_new_episodes',
            'monday_new_episodes',
            'tuesday_new_episodes',
            'wednesday_new_episodes',
            'thursday_new_episodes',
            'friday_new_episodes',
            'saturday_new_episodes'
        ]
        posts_tv = next((x['item'] for x in data if x['slug'] in slug_tv), [])
        posts_tv = [x for x in posts_tv if len(str(x['id'])) > 1]
        posts.extend(posts_tv)
    
    if region.lower() == "sg":
        items = list(map(parse, posts))
    elif region.lower() == "id":
        items = list(map(parse2, posts))
    return {
        'title': 'VIU New Titles',
        'link': 'https://www.viu.com',
        'description': 'New Titles on VIU',
        'author': 'pandamoon21',
        'items': items
    }