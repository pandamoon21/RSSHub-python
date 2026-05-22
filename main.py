import warnings
# Suppress pkg_resources deprecation noise from older Flask CLI tooling.
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="flask.cli",
)

import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from rsshub import create_app

# Resolve config: explicit FLASK_CONFIG wins, otherwise fall back to
# FLASK_ENV (development → development config, anything else → production).
config_name = os.getenv(
    'FLASK_CONFIG',
    'development' if os.getenv('FLASK_ENV') == 'development' else 'production',
)
app = create_app(config_name)

# Standard WSGI alias for Vercel / generic ASGI-WSGI loaders.
application = app


if __name__ == '__main__':
    app.run(debug=False, port=5000)
