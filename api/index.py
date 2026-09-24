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


class _DiagMiddleware:
    """TEMPORARY - delete once the Vercel routing is confirmed.

    Echoes the request as the function actually received it onto every response.
    An earlier version of this used a request header as the trigger and never fired,
    which says Vercel drops custom headers on the way through the rewrite - so the
    diagnostic has to ride the response instead, needing no trigger at all.
    """

    DIAG_HEADERS = ('x-diag-path', 'x-diag-script', 'x-diag-query',
                    'x-diag-method', 'x-diag-uri')

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        def _start(status, headers, exc_info=None):
            kept = [h for h in headers if h[0].lower() not in self.DIAG_HEADERS]
            kept.extend([
                ('X-Diag-Path', environ.get('PATH_INFO') or ''),
                ('X-Diag-Script', environ.get('SCRIPT_NAME') or ''),
                ('X-Diag-Query', environ.get('QUERY_STRING') or ''),
                ('X-Diag-Method', environ.get('REQUEST_METHOD') or ''),
                ('X-Diag-Uri', environ.get('RAW_URI') or environ.get('REQUEST_URI') or ''),
            ])
            return start_response(status, kept, exc_info)

        return self.wsgi_app(environ, _start)


app.wsgi_app = _DiagMiddleware(app.wsgi_app)

# Vercel picks up this name as the handler.
__all__ = ['app']
