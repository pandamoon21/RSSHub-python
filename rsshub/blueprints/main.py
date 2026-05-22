from flask import Blueprint, render_template, request

from rsshub.extensions import cache
from rsshub.utils import swr_cache

bp = Blueprint('main', __name__)


@bp.route('/')
def word():
    from rsshub.spiders.word.word import ctx
    return render_template('main/word.html', **ctx())


@bp.route('/index')
def index():
    return render_template('main/index.html')


@bp.route('/feeds')
def feeds():
    return render_template('main/feeds.html')


@bp.app_template_global()
def filter_content(ctx):
    """Apply optional URL-driven filters to the items collection.

    Supported query string parameters:
        include_title, include_description  -> match (use `|` for OR)
        exclude_title, exclude_description  -> remove (use `|` for OR)
        limit                               -> integer cap on item count
    """
    include_title = request.args.get('include_title')
    include_description = request.args.get('include_description')
    exclude_title = request.args.get('exclude_title')
    exclude_description = request.args.get('exclude_description')
    limit = request.args.get('limit', type=int)

    items = ctx['items'].copy()

    if include_title:
        keywords = include_title.split('|') if '|' in include_title else [include_title]
        items = [
            item for item in items
            if any(k in item['title'] for k in keywords)
        ]

    if include_description:
        keywords = (
            include_description.split('|')
            if '|' in include_description
            else [include_description]
        )
        items = [
            item for item in items
            if any(k in item['description'] for k in keywords)
        ]

    if exclude_title:
        keywords = exclude_title.split('|') if '|' in exclude_title else [exclude_title]
        items = [
            item for item in items
            if all(k not in item['title'] for k in keywords)
        ]

    if exclude_description:
        keywords = (
            exclude_description.split('|')
            if '|' in exclude_description
            else [exclude_description]
        )
        items = [
            item for item in items
            if all(k not in item['description'] for k in keywords)
        ]

    if limit:
        items = items[:limit]

    ctx = ctx.copy()
    ctx['items'] = items
    return ctx


# ---------- feed routes ----------

@bp.route('/naver/newmovies/')
@cache.cached(timeout=1800, query_string=True)
def naver_newmovies():
    from rsshub.spiders.naver.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/naver/broadcast/')
@cache.cached(timeout=1800, query_string=True)
def naver_series():
    from rsshub.spiders.naver.broadcast import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tving/newmovies/')
@cache.cached(timeout=1800, query_string=True)
def tving_newmovies():
    from rsshub.spiders.tving.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tving/series/')
@cache.cached(timeout=1800, query_string=True)
def tving_series():
    from rsshub.spiders.tving.series import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tving/series4k/')
@cache.cached(timeout=1800, query_string=True)
def tving_series4k():
    from rsshub.spiders.tving.series4k import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tving/movies4k/')
@cache.cached(timeout=1800, query_string=True)
def tving_movies4k():
    from rsshub.spiders.tving.movies4k import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tving/entertainment/')
@cache.cached(timeout=1800, query_string=True)
def tving_enter():
    from rsshub.spiders.tving.entertainment import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/seezn/contents/<string:menuid>')
@cache.cached(timeout=1800, query_string=True)
def seezn_contents(menuid=''):
    from rsshub.spiders.seezn.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx(menuid)))


@bp.route('/genietv/contents/<string:menuid>/<string:orderby>')
@cache.cached(timeout=1800, query_string=True)
def genietv_contents(menuid='', orderby=''):
    from rsshub.spiders.genietv.movies2 import ctx
    return render_template('main/atom.xml', **filter_content(ctx(menuid, orderby)))


@bp.route('/klikfilm/newmovies/<string:section>')
@cache.cached(timeout=1800, query_string=True)
def klikfilm_newmovies(section=''):
    from rsshub.spiders.klikfilm.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx(section)))


@bp.route('/wavve/series/<string:order>')
@cache.cached(timeout=1800, query_string=True)
def wavve_series(order=''):
    from rsshub.spiders.wavve.series import ctx
    return render_template('main/atom.xml', **filter_content(ctx(order)))


@bp.route('/wavve/moviesplus')
@cache.cached(timeout=1800, query_string=True)
def wavve_moviesplus():
    from rsshub.spiders.wavve.moviesplus import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/coupangplay/contents')
@cache.cached(timeout=1800, query_string=True)
def coupangplay_contents():
    from rsshub.spiders.coupangplay.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/amazon/kcontents')
@cache.cached(timeout=1800, query_string=True)
def amazon_kcontents():
    from rsshub.spiders.amazon.kcontents import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/netflix/korean')
@cache.cached(timeout=1800, query_string=True)
def netflix_korean():
    from rsshub.spiders.netflix.korean import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/ovagames/feeds')
@swr_cache(timeout=1800)
def ovagames_feeds():
    from rsshub.spiders.ovagames.feeds import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/sungai/han')
@cache.cached(timeout=1800, query_string=True)
def sungai_han():
    from rsshub.spiders.sungai.han import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/tokopedia/search')
@swr_cache(timeout=1800)
def tokopedia_search():
    """Tokopedia Search RSS with extensive query filtering.

    All parameters are passed via request arguments (query string).
    """
    from rsshub.spiders.tokopedia.search import ctx

    limit = request.args.get('limit', default=10, type=int)
    query = request.args.get('query', default="", type=str)
    bebas_ongkir_extra = request.args.get('bebas_ongkir_extra', default="", type=str)
    is_discount = request.args.get('is_discount', default="", type=str)
    condition = request.args.get('condition', default=0, type=int)
    shop_tier = request.args.get('shop_tier', default=0, type=int)
    pmin = request.args.get('pmin', default=0, type=int)
    pmax = request.args.get('pmax', default=0, type=int)
    is_fulfillment = request.args.get('is_fulfillment', default="", type=str)
    is_plus = request.args.get('is_plus', default="", type=str)
    cod = request.args.get('cod', default="", type=str)
    rt = request.args.get('rt', default=0.0, type=float)
    latest_product = request.args.get('latest_product', default=0, type=int)

    feed_context = ctx(
        limit=limit,
        query=query,
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

    return render_template('main/atom.xml', **filter_content(feed_context))


@bp.route('/viu/newtitles/<string:region>/<string:category>')
@cache.cached(timeout=1800, query_string=True)
def viu_newtitles(region='', category=''):
    from rsshub.spiders.viu.newtitles import ctx
    return render_template('main/atom.xml', **filter_content(ctx(region, category)))


@bp.route('/viu/simulcast/<string:limit>')
@cache.cached(timeout=1800, query_string=True)
def viu_simulcast(limit=''):
    from rsshub.spiders.viu.simulcast import ctx
    return render_template('main/atom.xml', **filter_content(ctx(limit)))


@bp.route('/watcha/neweps')
@cache.cached(timeout=1800, query_string=True)
def watcha_baru():
    from rsshub.spiders.watcha.neweps import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/kocowa/catalog/<string:catalogId>')
@cache.cached(timeout=1800, query_string=True)
def kocowa_contents(catalogId=''):
    from rsshub.spiders.kocowa.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx(catalogId)))


@bp.route('/fitgirl/feed')
@cache.cached(timeout=1800, query_string=True)
def fitgirl_feed():
    from rsshub.spiders.fitgirl.feed import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/filter/')
def rss_filter():
    from rsshub.spiders.rssfilter.filter import ctx
    feed_url = request.args.get("feed")
    return render_template('main/atom.xml', **filter_content(ctx(feed_url)))
