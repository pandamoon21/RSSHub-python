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
@bp.route('/cninfo/announcement/<string:stock_id>/<string:category>')
@bp.route('/cninfo/announcement')
def cninfo_announcement(stock_id='', category=''):
    from rsshub.spiders.cninfo.announcement import ctx
    return render_template('main/atom.xml', **filter_content(ctx(stock_id,category)))


@bp.route('/chuansongme/articles/<string:category>')
@bp.route('/chuansongme/articles')
def chuansongme_articles(category=''):
    from rsshub.spiders.chuansongme.articles import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))


@bp.route('/ctolib/topics/<string:category>')
@bp.route('/ctolib/topics')
def ctolib_topics(category=''):
    from rsshub.spiders.ctolib.topics import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))


@bp.route('/infoq/recommend')
def infoq_recommend():
    from rsshub.spiders.infoq.recommend import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/infoq/topic/<int:category>')
def infoq_topic(category=''):
    from rsshub.spiders.infoq.topic import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))


@bp.route('/dxzg/notice')
def dxzg_notice():
    from rsshub.spiders.dxzg.notice import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))


@bp.route('/earningsdate/prnewswire')
def earningsdate_prnewswire():
    from rsshub.spiders.earningsdate.prnewswire import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/earningsdate/globenewswire')
def earningsdate_globenewswire():
    from rsshub.spiders.earningsdate.globenewswire import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/earningsdate/businesswire')
def earningsdate_businesswire():
    from rsshub.spiders.earningsdate.businesswire import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/jiemian/newsflash/<string:category>')
def jiemian_newsflash(category=''):
    from rsshub.spiders.jiemian.newsflash import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/csrc/audit/<string:category>')
def csrc_audit(category=''):
    from rsshub.spiders.csrc.audit import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/caixin/scroll/<string:category>')
def caixin_scroll(category=''):
    from rsshub.spiders.caixin.scroll import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))    

@bp.route('/eastmoney/report/<string:type>/<string:category>')
def eastmoney_report(category='', type=''):
    from rsshub.spiders.eastmoney.report import ctx
    return render_template('main/atom.xml', **filter_content(ctx(type,category)))      

@bp.route('/xuangubao/<string:type>/<string:category>')
def xuangubao_xuangubao(type='', category=''):
    from rsshub.spiders.xuangubao.xuangubao import ctx
    return render_template('main/atom.xml', **filter_content(ctx(type, category)))        

@bp.route('/cls/subject/<string:category>')
def cls_subject(category=''):
    from rsshub.spiders.cls.subject import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category))) 

@bp.route('/cls/telegraph/')
def cls_telegraph():
    from rsshub.spiders.cls.telegraph import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))          

@bp.route('/chaindd/column/<string:category>')
def chaindd_column(category=''):
    from rsshub.spiders.chaindd.column import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))      

@bp.route('/techcrunch/tag/<string:category>')
def techcrunch_tag(category=''):
    from rsshub.spiders.techcrunch.tag import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/weiyangx/home')
def weiyangx_home():
    from rsshub.spiders.weiyangx.home import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/weiyangx/express/')
def weiyangx_express():
    from rsshub.spiders.weiyangx.express import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/weiyangx/tag/<string:category>')
def weiyangx_tag(category=''):
    from rsshub.spiders.weiyangx.tag import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/jintiankansha/column/<string:category>')
def jintiankansha_column(category=''):
    from rsshub.spiders.jintiankansha.column import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))    

@bp.route('/interotc/cpgg/<string:category>')
def interotc_cpgg(category=''):
    from rsshub.spiders.interotc.cpgg import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))    

@bp.route('/benzinga/ratings/<string:category>')
def benzinga_ratings(category=''):
    from rsshub.spiders.benzinga.ratings import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))     

@bp.route('/chouti/section/<string:category>')       
def chouti_section(category=''):
    from rsshub.spiders.chouti.section import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/chouti/search/<string:category>')       
def chouti_search(category=''):
    from rsshub.spiders.chouti.search import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/chouti/user/<string:category>')       
def chouti_user(category=''):
    from rsshub.spiders.chouti.user import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/zaobao/realtime/<string:category>')
def zaobao_realtime(category=''):
    from rsshub.spiders.zaobao.realtime import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/mp/tag/<string:mp>/<string:tag>')
def mp_tag(mp='', tag=''):
    from rsshub.spiders.mp.tag import ctx
    return render_template('main/atom.xml', **filter_content(ctx(mp,tag)))

@bp.route('/producthunt/search/<string:keyword>/<string:period>')
def producthunt_search(keyword='', period=''):
    from rsshub.spiders.producthunt.search import ctx
    return render_template('main/atom.xml', **filter_content(ctx(keyword,period)))

@bp.route('/pgyer/<string:category>')
def pgyer_app(category=''):
    from rsshub.spiders.pgyer.app import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/economist/worldbrief')
def economist_wordlbrief(category=''):
    from rsshub.spiders.economist.worldbrief import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

@bp.route('/mp/gh/<string:gh>')
def mp_gh(gh=''):
    from rsshub.spiders.mp.gh import ctx
    return render_template('main/atom.xml', **filter_content(ctx(gh)))    

@bp.route('/mp/youwuqiong/<string:author>')
def mp_youwuqiong(author=''):
    from rsshub.spiders.mp.youwuqiong import ctx
    return render_template('main/atom.xml', **filter_content(ctx(author)))        

@bp.route('/yfchuhai/express/')
def yfchuhai_express():
    from rsshub.spiders.yfchuhai.express import ctx
    return render_template('main/atom.xml', **filter_content(ctx())) 

@bp.route('/bjnews/<string:category>')
def bjnews_channel(category=''):
    from rsshub.spiders.bjnews.channel import ctx
    return render_template('main/atom.xml', **filter_content(ctx(category)))

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
    from rsshub.spiders.genietv.movies import ctx
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

@bp.route('/watcha/neweps')
def watcha_neweps():
    from rsshub.spiders.watcha.neweps import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/amazon/kcontents')
def amazon_kcontents():
    from rsshub.spiders.amazon.kcontents import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/netflix/korean')
def netflix_korean():
    from rsshub.spiders.netflix.korean import ctx
    return render_template('main/atom.xml', **filter_content(ctx()))

@bp.route('/viu/newtitles/<string:region>')
def viu_newtitles(region=''):
    from rsshub.spiders.viu.newtitles import ctx
    return render_template('main/atom.xml', **filter_content(ctx(region)))

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