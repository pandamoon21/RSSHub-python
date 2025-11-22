from flask import Blueprint, render_template, request

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
    include_title = request.args.get('include_title')
    include_description = request.args.get('include_description')
    exclude_title = request.args.get('exclude_title')
    exclude_description = request.args.get('exclude_description')
    limit = request.args.get('limit', type=int)
    items = ctx['items'].copy()
    items = [item for item in items if include_title in item['title']] if include_title else items
    items = [item for item in items if include_description in item['description']] if include_description else items
    items = [item for item in items if exclude_title not in item['title']] if exclude_title else items
    items = [item for item in items if exclude_description not in item['description']] if exclude_description else items
    items = items[:limit] if limit else items
    ctx = ctx.copy()
    ctx['items'] = items
    return ctx



#---------- feed路由从这里开始 -----------#
@bp.route('/naver/newmovies/')
def naver_newmovies():
    from rsshub.spiders.naver.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/naver/broadcast/')
def naver_series():
    from rsshub.spiders.naver.broadcast import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tving/newmovies/')
def tving_newmovies():
    from rsshub.spiders.tving.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tving/series/')
def tving_series():
    from rsshub.spiders.tving.series import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tving/series4k/')
def tving_series4k():
    from rsshub.spiders.tving.series4k import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tving/movies4k/')
def tving_movies4k():
    from rsshub.spiders.tving.movies4k import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tving/entertainment/')
def tving_enter():
    from rsshub.spiders.tving.entertainment import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/seezn/contents/<string:menuid>')
def seezn_contents(menuid=''):
    from rsshub.spiders.seezn.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx(menuid)))

@bp.route('/genietv/contents/<string:menuid>/<string:orderby>')
def genietv_contents(menuid='', orderby=''):
    from rsshub.spiders.genietv.movies2 import ctx
    return render_template('main/atom.xml', **filter_content(ctx(menuid,orderby)))

@bp.route('/klikfilm/newmovies/<string:section>')
def klikfilm_newmovies(section=''):
    from rsshub.spiders.klikfilm.newmovies import ctx
    return render_template('main/atom.xml', **filter_content(ctx(section)))

@bp.route('/wavve/series/<string:order>')
def wavve_series(order=''):
    from rsshub.spiders.wavve.series import ctx
    return render_template('main/atom.xml', **filter_content(ctx(order)))

@bp.route('/wavve/moviesplus')
def wavve_moviesplus():
    from rsshub.spiders.wavve.moviesplus import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/coupangplay/contents')
def coupangplay_contents():
    from rsshub.spiders.coupangplay.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/amazon/kcontents')
def amazon_kcontents():
    from rsshub.spiders.amazon.kcontents import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/netflix/korean')
def netflix_korean():
    from rsshub.spiders.netflix.korean import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/sungai/han')
def sungai_han():
    from rsshub.spiders.sungai.han import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/tokopedia/search')
def tokopedia_search():
    """
    Tokopedia Search RSS with extensive query filtering.
    All parameters are passed via request arguments (query string).
    """
    from rsshub.spiders.tokopedia.search import ctx
    
    # 1. Extract and convert parameters from request.args
    # Note: Flask's request.args.get(..., type=int/float) handles conversion and None if missing/invalid.
    # The default values are set here, but the spider should handle logic for missing parameters.
    
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

    # 2. Call the spider's context function with all extracted arguments
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
        latest_product=latest_product
    )

    # 3. Apply general RSS filtering (if any additional filters are in the URL) and render
    return render_template('main/atom.xml', **filter_content(feed_context))

@bp.route('/viu/newtitles/<string:region>/<string:category>')
def viu_newtitles(region='', category=''):
    from rsshub.spiders.viu.newtitles import ctx
    return render_template('main/atom.xml', **filter_content(ctx(region,category)))

@bp.route('/viu/simulcast/<string:limit>')
def viu_simulcast(limit=''):
    from rsshub.spiders.viu.simulcast import ctx
    return render_template('main/atom.xml', **filter_content(ctx(limit)))

@bp.route('/watcha/neweps')
def watcha_baru():
    from rsshub.spiders.watcha.neweps import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/kocowa/catalog/<string:catalogId>')
def kocowa_contents(catalogId=''):
    from rsshub.spiders.kocowa.contents import ctx
    return render_template('main/atom.xml', **filter_content(ctx(catalogId)))

@bp.route('/filter/')
def rss_filter():
    from rsshub.spiders.rssfilter.filter import ctx
    feed_url = request.args.get("feed")  
    return render_template('main/atom.xml', **filter_content(ctx(feed_url)))

'''
@bp.route('/test')
@bp.route('/test/测试')
def test():
    import sys
    # return sys.getdefaultencoding()
    return sys.stdout.encoding
'''