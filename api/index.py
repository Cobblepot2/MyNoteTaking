"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI callable named `app` in the file under
api/ and forwards every request here (see vercel.json). Flask then handles routing,
including serving the front-end from src/static/.
"""

import os
import sys

# Put the project root on the path so `src.*` and `prompts/` resolve inside the
# function bundle. Must happen before importing src.main.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app  # noqa: E402  (import has to follow the sys.path fix)


class _RewritePathMiddleware:
    """Undo the prefix that the Vercel rewrite adds to the request path.

    vercel.json sends every request to `/api/index/:path*`, and Vercel does not
    forward the original path in any header, so without this Flask would only ever
    see `/api/index/...` and every route would fall through to the catch-all.
    """

    PREFIX = '/api/index'

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path == self.PREFIX:
            environ['PATH_INFO'] = '/'
        elif path.startswith(self.PREFIX):
            environ['PATH_INFO'] = path[len(self.PREFIX):] or '/'
        return self.wsgi_app(environ, start_response)


app.wsgi_app = _RewritePathMiddleware(app.wsgi_app)

# Vercel picks up this name as the handler.
__all__ = ['app']
