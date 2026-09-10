# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask app that generates RSS/Atom feeds for sites that don't provide them. A Python port of
[DIYgod/RSSHub](https://github.com/DIYgod/RSSHub) (`rsshub` package: 79 spider dirs, ~143 routes).

Two remotes:
- `origin` — `pandamoon21/RSSHub-python` (this fork; where work is pushed)
- `upstream` — `hillerliao/RSSHub-python` (the base project this fork merges from)

The fork carries custom Korean-entertainment / game-repack spiders (naver, tving, seezn, genietv,
klikfilm, wavve, coupangplay, amazon, netflix, ovagames, sungai, tokopedia, viu, watcha, kocowa,
fitgirl, shopee) on top of upstream's Chinese financial/news spiders. Both sets coexist.

## Commands

```bash
# Run (dev) — needs .env or defaults to production config
flask run                      # FLASK_APP/FLASK_ENV come from .flaskenv

# Run (prod)
gunicorn main:app -b 0.0.0.0:5000
docker build -t pyrsshub . && docker run -dit --name pyrsshub -p 8080:80 pyrsshub

# Tests (unittest — there is no pytest)
python -m unittest discover -s tests
python -m unittest tests.test_errors.ErrorsTestCase.test_500   # single test
```

There is no configured linter in the repo (no ruff/flake8 config); `pyproject.toml` lists `yapf` and
`pylint` as optional dev dependencies but nothing enforces them.

Dependencies are duplicated across `requirements.txt` (this fork's pinned set, no Playwright),
`requirements-lite.txt`, `requirements-full.txt` (Playwright/PDF — used by the Dockerfile),
`pyproject.toml` and `uv.lock`. The README says Vercel uses `requirements-lite.txt`, but
`vercel.json` doesn't actually select it. Adding a dependency means touching the relevant
`requirements*` file as well as `pyproject.toml`, or the deploy path won't see it.

## Architecture

**App factory** (`rsshub/__init__.py`): `create_app(config_name)` — config from `rsshub/config.py`
(`development`/`testing`/`production`), registers the `main` and `proxy` blueprints, error handlers,
and swaps `app.response_class` to `XMLResponse` (in `rsshub/utils.py`) which auto-sets the
`application/xml` mimetype for `<?xml` bodies.

**Spider contract** (the thing that matters most): each spider is a module exposing `ctx(...)` that
returns a plain dict:

```python
{'title', 'link', 'description', 'author', 'items': [{'title','description','link','pubDate'}, ...]}
```

`rsshub/templates/main/atom.xml` renders that dict. `item.description` and `item.title` are injected
with `|safe`, so spiders embed raw HTML there by convention (images via
`<img referrerpolicy='no-referrer' ...>`). Undefined optional keys render empty rather than raising.

**Routes** live in `rsshub/blueprints/main.py` — one hand-written view per spider, importing `ctx`
*inside* the function body (lazy import). The route wires up cache + filtering:

```python
@bp.route('/foo/bar/<string:x>')
@cache.cached(timeout=1800, query_string=True)
def foo_bar(x=''):
    from rsshub.spiders.foo.bar import ctx
    return render_template('main/atom.xml', **filter_content(ctx(x)))
```

`filter_content` is an `@bp.app_template_global()` that reads `include_title` / `exclude_title` /
`include_description` / `exclude_description` / `limit` from the query string and filters `ctx['items']`.
Some routes call `ctx()` directly without it — keep whatever the neighbouring route does.

**Caching** (`rsshub/utils.py`): `@swr_cache(timeout=N)` is a stale-while-revalidate decorator — serves
the cached value and refreshes in a background thread when stale. Use it (over `@cache.cached`) for slow
or flaky upstreams. It calls `current_app._get_current_object()` and re-enters a request context in the
worker thread, so it must not be used outside a request. `@cache.cached(...)` is the plain alternative.

**A new spider means four edits**, and they're easy to miss: (1) the spider module, (2) the route in
`rsshub/blueprints/main.py`, (3) the doc card in `rsshub/templates/main/feeds.html`, and (4) the route
sample in the `const feeds = [...]` array in `rsshub/templates/main/status.html` — `/status` is a
hardcoded list, not derived from the route map, so new routes are invisible there until added.

**Deployment quirks**: `vercel.json` points the whole app at `main.py` and sets `PYTHONPATH`; Vercel
runs the lite subset (no Playwright). Geoblocked upstreams need a proxy — e.g. the genietv spider
accepts `?proxy=` or `$GENIETV_PROXY` for its Korea-only KT hosts.

## Conventions

- Spider output text is English (feed titles/descriptions/UI). Chinese inside URLs or query params
  (search keywords, upstream category names) is intentional — those are values sent to the upstream.
- Timestamps: `pubDate` is a string `YYYY-MM-DD HH:mm:ss`; spiders use `arrow` to format.
- The Feeds page (`feeds.html`) is one `<div class="card text-left"><div class="card-body">` block per
  feed with `<!--item info start-->` / `<!--item info end-->` markers. Preserve that wrapper — a missing
  one renders the card with no border.
- Merge upstream freely; custom spiders live in dirs that upstream doesn't have, so conflicts there
  are rare. `rsshub/utils.py` `fetch()` returns **BeautifulSoup**, and spiders call `.select()` on it
  (not parsel `.css()`) — check which API a spider uses before changing `fetch`.
