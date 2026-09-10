# RSSHub-python

A lightweight, extensible RSS generator written in Python using Flask. This project is a Python implementation of the original [RSSHub](https://github.com/DIYgod/RSSHub).

## Project Overview

- **Purpose:** Generate RSS/Atom feeds for websites that don't provide them.
- **Architecture:** 
    - **Spiders:** Located in `rsshub/spiders/`. Each spider is responsible for fetching and parsing data from a specific source.
    - **Blueprints:** Routing is handled in `rsshub/blueprints/main.py`.
    - **Templates:** XML/HTML templates are in `rsshub/templates/`. The primary template for feeds is `main/atom.xml`.
    - **Caching:** Uses `flask-caching` with a custom Stale-While-Revalidate (`swr_cache`) decorator in `rsshub/utils.py`.
- **Technologies:** Flask, Requests, Parsel (Scrapy's selector), BeautifulSoup4, Arrow (date/time), TinyDB.

## Building and Running

### Development
1.  **Dependencies:** The project uses `requirements.txt`, `Pipfile`, and `pyproject.toml`.
2.  **Environment:**
    ```bash
    pipenv install --dev
    pipenv shell
    flask run
    ```
    *Alternatively, if using `uv`:*
    ```bash
    uv pip install -r requirements.txt
    flask run
    ```
3.  **Config:** Configuration is managed in `rsshub/config.py`. Use `.env` for secrets.

### Testing
- Run tests using:
    ```bash
    python -m unittest discover
    ```

### Production
- Deploy using Gunicorn:
    ```bash
    gunicorn main:app -b 0.0.0.0:5000
    ```
- Docker deployment is supported via the provided `Dockerfile`.

## Development Conventions

### Adding a New Spider
1.  Create a new directory/script under `rsshub/spiders/`.
2.  Implement a `ctx` function that returns a dictionary:
    ```python
    {
        'title': 'Feed Title',
        'link': 'https://example.com',
        'description': 'Feed Description',
        'author': 'Author Name',
        'items': [
            {
                'title': 'Item Title',
                'description': 'Item Content (HTML)',
                'link': 'Item URL',
                'pubDate': 'YYYY-MM-DD HH:mm:ss'
            },
            ...
        ]
    }
    ```
3.  Register the route in `rsshub/blueprints/main.py`.
4.  Add documentation to `rsshub/templates/main/feeds.html`.

### Caching and Filtering
- **SWR Cache:** Use the `@swr_cache(timeout=...)` decorator for routes that involve heavy scraping or slow APIs.
- **Content Filtering:** Routes should pass the `ctx()` result through `filter_content()` in the template call to support URL-driven filtering (`include_title`, `exclude_title`, etc.).
  ```python
  return render_template('main/atom.xml', **filter_content(ctx()))
  ```

### Utility Helpers
- Use `rsshub.utils.fetch(url)` for a consistent scraping interface returning a Parsel Selector.
- Use `rsshub.utils.DEFAULT_HEADERS` to avoid being blocked by simple User-Agent checks.
