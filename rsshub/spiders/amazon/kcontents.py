import re
import requests
from rsshub.utils import DEFAULT_HEADERS

def parse(post):
    item = {}
    judul_tahun = re.findall(r"(?<=a-text-normal\">)(.*?)(?=</span>)", post)
    judul = judul_tahun[0].replace("&#x27;", "\'")
    if len(judul) > 1:
        tahun = judul_tahun[-1]
        judul += f" {tahun}"
    item['title'] = "{}".format(judul)
    img_ = re.search(r"(?<=srcset=\")(.*?)(?=\")", post).group(1)
    img_list = img_.split(", ")
    img_new = []
    for i in img_list:
        imgnew = i.split(" ")
        img_new.append({
            "size": imgnew[1],
            "url": imgnew[0]
        })
    imgurl = next(x["url"] for x in img_new if x["size"] == "3x")
    asin = re.search(r"(?<=data-asin=\")(.*?)(?=\")", post).group(1)
    link = f"https://watch.amazon.com/watch?asin={asin}"
    jenis = re.search(r"(?<=a-spacing-top-mini).*<span>(.*?)(?=</span>)", post)
    if jenis:
        jenis = jenis.group(1).replace("$0.00 with a ", "")
    else:
        jenis = "Buy/Rent only"
    price_rent = re.search(r"(?<=a-offscreen\">)(.*?)(?=</span>)", post)
    harga = ""
    if price_rent:
        harga += f"- Rent: {price_rent.group(1)}"
    price_buy = re.search(r"From (\$\d+\.\d+) to buy", post)
    if price_buy:
        harga += f" - Buy: {price_buy.group(1)}"
    item['description'] = "{a}<br>{b}<br>{c}".format(
        a=f"Type: {jenis} {harga}",
        b=f"<a href='{link}'>Link contents</a>",
        c=f"<img referrerpolicy='no-referrer' src='{imgurl}'>"
    )
    item['link'] = link
    return item


def ctx():
    DEFAULT_HEADERS.update({
        "Origin": "https://www.amazon.com",
        "Referer": "https://www.amazon.com/",
    })
    url = 'https://www.amazon.com/s'
    posts = requests.get(
        url=url,
        headers=DEFAULT_HEADERS,
        params={
            "i": "instant-video",
            "bbn": "2858778011",
            "rh": "n:2625373011,n:2858778011,p_n_feature_seven_browse-bin:23855137011",
            "s": "date-desc-rank",
            "dc": "",
            "ds": "v1:lSP5CbSIMAo4D6lXHPYnhuUHqmYO/bidVrUmQyqPhLI",
            "crid": "WYDMIB13SGTQ",
            "qid": "1662890967",
            "sprefix": "uninvited,instant-video,365",
            "ref": "sr_ex_n_1"
        }
    ).text
    re_title = r"<div data-asin=\".*?</span></li></ul></div></div></div></div></div></div></div></div></div></div></div></div></div>"
    titles = re.findall(re_title, posts)
    items = list(map(parse, titles))
    return {
        'title': 'Amazon New Korean Contents',
        'link': 'https://www.amazon.com',
        'description': 'New Korean Contents on Amazon or Primevideo',
        'author': 'pandamoon21',
        'items': items
    }