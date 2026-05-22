import os

from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_caching import Cache


bootstrap = Bootstrap()
moment = Moment()

# Only import and initialize the debug toolbar in development.
# This keeps production / serverless deployments lean.
debugtoolbar = None
if os.environ.get('FLASK_ENV') == 'development':
    try:
        from flask_debugtoolbar import DebugToolbarExtension
        debugtoolbar = DebugToolbarExtension()
    except ImportError:
        pass

cache = Cache(config={
    "DEBUG": True,
    "CACHE_TYPE": "simple",
    "CACHE_DEFAULT_TIMEOUT": 3600,
})
