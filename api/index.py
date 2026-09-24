"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI callable named `app` in the file under
api/ and forwards every request here (see vercel.json). Flask then handles routing,
including serving the front-end from src/static/.
"""

import json
import os
import sys

# Put the project root on the path so `src.*` and `prompts/` resolve inside the
# function bundle. Must happen before importing src.main.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app  # noqa: E402  (import has to follow the sys.path fix)


class _DiagMiddleware:
    """TEMPORARY - delete once the Vercel routing is confirmed.

    Wrapping the WSGI app sits *outside* Flask, so it answers even when the rewrite
    sends every request to the wrong route. Triggered by a request header rather than
    a path, because the path is exactly what is in question.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get('HTTP_X_DIAG') != '1':
            return self.wsgi_app(environ, start_response)

        payload = {
            key: environ.get(key)
            for key in ('PATH_INFO', 'SCRIPT_NAME', 'QUERY_STRING',
                        'REQUEST_METHOD', 'RAW_URI', 'HTTP_HOST')
        }
        payload['headers'] = {
            key[5:].replace('_', '-').lower(): value
            for key, value in environ.items()
            if key.startswith('HTTP_')
        }

        body = json.dumps(payload, indent=2).encode('utf-8')
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ])
        return [body]


app.wsgi_app = _DiagMiddleware(app.wsgi_app)

# Vercel picks up this name as the handler.
__all__ = ['app']
