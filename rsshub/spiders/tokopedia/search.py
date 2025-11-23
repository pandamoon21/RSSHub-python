import requests

from typing import Optional
from rsshub.utils import DEFAULT_HEADERS
from tokopaedi import search, SearchFilters, get_product, get_reviews

def format_weight(weight, unit):
    # Normalize everything to grams first
    if unit == "KG" or unit == "KILOGRAM":
        grams = weight * 1000
    else:
        grams = weight

    # Logic: If >= 1000g, show as KG, otherwise G
    if grams >= 1000:
        kg_value = grams / 1000
        # Remove .0 if it's a whole number (e.g., 2.0 -> 2)
        formatted_kg = int(kg_value) if kg_value.is_integer() else kg_value
        return f"{formatted_kg} KG"
    else:
        # Remove .0 if it's a whole number
        formatted_g = int(grams) if isinstance(grams, float) and grams.is_integer() else grams
        return f"{formatted_g} G"
    

def parse(post):
    item = {}
    product_name = post["product_name"]
    price_text = post["price_text"]
    item['title'] = f"{product_name} - {price_text}"
    prod_desc = (post.get("description") or "").replace("\n", "<br>")
    prod_url = post["url"].split("?")[0]
    prod_price_original = post.get("price_original", price_text)
    prod_discount = post.get("discount_percentage") or "-"
    prod_stock = post.get("total_stock") or 0
    prod_status = post["status"]
    prod_weight = format_weight(
        post.get("weight") or 0,
        post.get("weight_unit") or "GRAM"
    )
    prod_sold_count = post["sold_count"]
    prod_category = post["category"]
    shop_url = post["shop"]["url"]
    shop_name = post["shop"]["name"]
    shop_city = post["shop"]["city"]
    shop_type = post["shop"]["shop_type"]
    prod_rincian = "{a}, Price: {b}, Price Ori: {c}, Discount: {d}<br>Stock: {e}, Sold: {f}<br>Weight: {g}, Category: {h}".format(
        a=prod_status,
        b=price_text,
        c=prod_price_original,
        d=prod_discount,
        e=prod_stock,
        f=prod_sold_count,
        g=prod_weight,
        h=prod_category
    )
    shop_rincian = f"Toko: {shop_name} ({shop_type}), City: {shop_city}"
    images = post["product_media"]
    if not images:
        main_image = post["main_image"]
        images_html = f"<img referrerpolicy='no-referrer' src='{main_image}'><br>"
    else:
        images_html = ""
        for image in images:
            imgurl = image.get("original")
            if imgurl:
                images_html += f"<img referrerpolicy='no-referrer' src='{imgurl}'><br>"
    item['description'] = "{a}<br>{b}<br>{c}<br>{d}".format(
        a=f"<a href='{prod_url}'>Tokped link</a> - <a href='{shop_url}'>{shop_name}</a>",
        b=f"{shop_rincian}<br>{prod_rincian}",
        c=f"Description:<br>{prod_desc}<br>",
        d=images_html
    )
    item['link'] = prod_url
    item['author'] = shop_name
    return item


def ctx(
        limit=10,
        query="",
        bebas_ongkir_extra: Optional[bool] = None,
        is_discount: Optional[bool] = None,
        condition: Optional[int] = None,    # 1 = new, 2 = used
        shop_tier: Optional[int] = None,    # 2 = mall, 3 = power merchant
        pmin: Optional[int] = None,         # minimum price filter
        pmax: Optional[int] = None,         # maximum price filter
        is_fulfillment: Optional[bool] = None,  # dilayani tokopedia
        is_plus: Optional[bool] = None,     # tokopedia plus
        cod: Optional[bool] = None,
        rt: Optional[float] = None,         # rating filter (0.0 to 5.0)
        # Product age in days
        # 7  = added in the last 7 days
        # 30 = added in the last 30 days
        # 90 = added in the last 90 days
        latest_product: Optional[int] = None,
        debug_: Optional[bool] = False
    ):
    data = search(
        query,
        max_result=limit,
        debug=debug_,
        filters=SearchFilters(
            bebas_ongkir_extra=bebas_ongkir_extra,
            is_discount=is_discount,
            condition=condition,
            shop_tier=shop_tier,
            pmin=pmin,
            pmax=pmax,
            is_fulfillment=is_fulfillment,
            is_plus=is_plus,
            cod=cod,
            rt=rt,
            latest_product=latest_product,
        )
    )
    # data.enrich_details(debug=False)
    posts = data.json()
    items = list(map(parse, posts))
    return {
        'title': 'Tokopedia Search Results',
        'link': "https://www.tokopedia.com",
        'description': 'Tokopedia Search Results',
        'author': 'pandamoon21',
        'items': items
    }