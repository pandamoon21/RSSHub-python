import requests
from datetime import date
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    judul = post['title']
    jenis = post["vtype"]
    tahun = post["year"]
    item['title'] = "{} {} - {}".format(judul, tahun, jenis)
    synopsis = post["synopsis"]
    imgurl = post['img']
    nfid = post["nfid"]
    link = f"https://www.netflix.com/watch/{nfid}"
    try:
        clist = requests.get(
            url=f"https://unogs.com/api/title/countries",
            params={"netflixid": nfid},
            headers=DEFAULT_HEADERS
        ).json()
        countrylist = [x["country"] for x in clist]
    except Exception:
        clist = post["clist"].replace('"', "").split(",")
        countrylist = [x.split(":")[-1] for x in clist]
    countries = ", ".join(countrylist)
    item['description'] = "{a}<br>{b}".format(
        a=f"NFID: {nfid}\nCountries: {countries}\n{synopsis}",
        b=f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    item['author'] = "pandamoon21"
    titledate = post["titledate"]
    date = f"{titledate} 01:00:00"
    item['pubDate'] = date
    return item


def ctx():
    DEFAULT_HEADERS.update({
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2NjQwODAyNjAsIm5iZiI6MTY2NDA4MDI2MCwianRpIjoiZjU4NWRkMWMtMGY1MS00ZmMyLWI1MTAtY2FiOTZlM2VmZTUwIiwiZXhwIjoxNjY0MTY2NjYwLCJpZGVudGl0eSI6IjE2NjQwODAyNjAuOTUxIiwiZnJlc2giOmZhbHNlLCJ0eXBlIjoiYWNjZXNzIn0.jn6tl_GG2Ap2DLZ07B7uZfaTQHr1dDSdYHV2_4HUAn0",
            "cookie": "authtoken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE2NjQwODAyNjAsIm5iZiI6MTY2NDA4MDI2MCwianRpIjoiZjU4NWRkMWMtMGY1MS00ZmMyLWI1MTAtY2FiOTZlM2VmZTUwIiwiZXhwIjoxNjY0MTY2NjYwLCJpZGVudGl0eSI6IjE2NjQwODAyNjAuOTUxIiwiZnJlc2giOmZhbHNlLCJ0eXBlIjoiYWNjZXNzIn0.jn6tl_GG2Ap2DLZ07B7uZfaTQHr1dDSdYHV2_4HUAn0; eucookie=stupideulaw; countrylist=267",
            "referer": "https://unogs.com",
            "referrer": "http://unogs.com"
        })
    url = "https://unogs.com/api/search"
    posts = requests.get(
        url=url,
        params={
            "limit": "20",
            "offset": "0",
            "query": "",
            "countrylist": "46,21,23,26,29,33,36,307,45,39,327,331,334,265,337,336,269,267,357,378,65,67,390,392,268,400,408,412,447,348,270,73,34,425,432,436,78",
            "country_andorunique": "or",
            "start_year": "1900",
            "end_year": date.today().year,
            "start_rating": "",
            "end_rating": "10",
            "genrelist": "",
            "type": "",
            "audio": "Korean [Original]",
            "subtitle": "",
            "audiosubtitle_andor": "or",
            "person": "",
            "filterby": "",
            "orderby": ""
        },
        headers=DEFAULT_HEADERS
    )
    posts = posts.json()['results']
    items = list(map(parse, posts))
    return {
        'title': 'Netflix new Korean Contents',
        'link': 'https://unogs.com/',
        'description': 'New Korean Contents on Netflix with Unogs',
        'author': 'pandamoon21',
        'items': items
    }