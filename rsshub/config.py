import os
import sys


basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class BaseConfig:
    SITE_NAME = 'RSSHub'
    GITHUB_USERNAME = 'pandamoon21'
    EMAIL = '33972938+pandamoon21@users.noreply.github.com'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'f43hrt53et53'
    DEBUG_TB_INTERCEPT_REDIRECTS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = 'development'


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV = 'production'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
