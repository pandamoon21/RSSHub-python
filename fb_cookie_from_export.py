#!/usr/bin/env python3
"""Convert a browser-exported Facebook cookie file into a FACEBOOK_COOKIE value.

Browser cookie exports (EditThisCookie, Cookie-Editor, "Get cookies.txt", devtools)
are JSON arrays of objects with many fields. The spiders need the same value in HTTP
Cookie header form, which is just the ``name=value`` pairs joined by ``"; "``.

Usage
-----
    python fb_cookie_from_export.py fb_cookies.json
    python fb_cookie_from_export.py fb_cookies.json --all
    python fb_cookie_from_export.py cookies.txt
    cat fb_cookies.json | python fb_cookie_from_export.py -

The result is printed to stdout, ready to paste into a hosting provider's environment
variable field (Vercel, Docker, Fly, etc.). Nothing is written to disk and no network
request is made.

Security
--------
The output is a live session credential — anyone holding it can act as that account.
It is printed to your terminal on purpose; avoid committing it, pasting it into an
issue, or piping it into a file that is tracked by git.
"""
import argparse
import json
import re
import sys

# Facebook only needs these two to authenticate; the rest are optional browser state.
REQUIRED_COOKIES = ('c_user', 'xs')


def parse_export(raw):
    """Parse a cookie export into a list of {name, value} dicts.

    Supports the JSON array/object formats produced by common browser extensions,
    and Netscape ``cookies.txt`` (the format curl and yt-dlp consume).
    """
    text = raw.strip()
    if not text:
        raise ValueError('the input is empty')

    if text.startswith(('[', '{')):
        return _parse_json(text)

    cookies = _parse_netscape(text)
    if cookies:
        return cookies

    # Neither JSON nor Netscape: say so, rather than reporting a Netscape-specific
    # failure for something that was never in that format.
    raise ValueError(
        'unrecognised cookie file format. Expected either a JSON export (starting with '
        "'[' or '{') or a Netscape cookies.txt (tab-separated). The input instead began "
        f'with: {text[:60]!r}'
    )


def _parse_json(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'not valid JSON: {exc}') from exc

    # Some extensions wrap the array in an object, e.g. {"cookies": [...]}.
    if isinstance(data, dict):
        for key in ('cookies', 'Cookies', 'data'):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # A plain {"name": "value"} mapping.
            pairs = []
            for name, value in data.items():
                if isinstance(value, str):
                    pairs.append({'name': name, 'value': value})
            if pairs:
                return pairs
            raise ValueError('unrecognised JSON object; expected a list of cookies')

    if not isinstance(data, list):
        raise ValueError('expected a JSON array of cookie objects')

    cookies = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        value = entry.get('value')
        if name and value is not None:
            cookies.append({'name': name, 'value': value})
    if not cookies:
        raise ValueError('no cookies with a name and value were found')
    return cookies


def _parse_netscape(text):
    """Parse the Netscape cookies.txt format: domain, flag, path, secure, expiry, name, value."""
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        # Skip comments, the "#HttpOnly_" prefix lines are handled below.
        if not line:
            continue
        if line.startswith('#HttpOnly_'):
            line = line[len('#HttpOnly_'):]
        elif line.startswith('#'):
            continue

        parts = line.split('\t')
        if len(parts) < 7:
            continue
        name, value = parts[5], parts[6]
        if name:
            cookies.append({'name': name, 'value': value})
    # Callers distinguish "not Netscape" from "malformed"; return what was found.
    return cookies


def build_cookie_value(cookies, include_all=False):
    """Return the FACEBOOK_COOKIE value.

    By default only c_user and xs are included: those are what Facebook uses to
    authenticate, and a shorter value is less likely to be truncated when pasted.
    """
    by_name = {}
    for cookie in cookies:
        # Later entries win, matching how a browser applies an updated cookie.
        by_name[cookie['name']] = cookie['value']

    if include_all:
        selected = cookies
    else:
        missing = [n for n in REQUIRED_COOKIES if n not in by_name]
        if missing:
            raise ValueError(
                'this export is missing the required cookie(s): '
                + ', '.join(missing)
                + '. Log in to Facebook in the browser you exported from, and make sure '
                  'the export includes HttpOnly cookies (xs is HttpOnly and is often '
                  'excluded by default).'
            )
        selected = [{'name': n, 'value': by_name[n]} for n in REQUIRED_COOKIES]

    return '; '.join(f"{c['name']}={c['value']}" for c in selected)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Turn a browser Facebook cookie export into a FACEBOOK_COOKIE value.')
    parser.add_argument(
        'path',
        help='cookie file (JSON export or Netscape cookies.txt), or - to read stdin')
    parser.add_argument(
        '--all', action='store_true',
        help='include every cookie instead of only c_user and xs (not usually needed)')
    parser.add_argument(
        '--quiet', action='store_true',
        help='print only the value, with no explanatory preamble')
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.path == '-' else open(
            args.path, encoding='utf-8', errors='replace').read()
    except OSError as exc:
        print(f'error: cannot read {args.path}: {exc}', file=sys.stderr)
        return 2

    try:
        cookies = parse_export(raw)
        value = build_cookie_value(cookies, include_all=args.all)
    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    if not args.quiet:
        names = [c['name'] for c in cookies]
        kept = re.findall(r'(?:^|; )([^=]+)=', value)
        print(f'# found {len(names)} cookie(s): {", ".join(names)}', file=sys.stderr)
        print(f'# using {len(kept)}: {", ".join(kept)} ({len(value)} chars)', file=sys.stderr)
        print('# paste the line below as the FACEBOOK_COOKIE value, without quotes:',
              file=sys.stderr)
    print(value)
    return 0


if __name__ == '__main__':
    sys.exit(main())
