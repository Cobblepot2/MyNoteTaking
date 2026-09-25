"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI callable named `app` in the file under
api/ and forwards every request here (see vercel.json). Flask then handles routing,
including serving the front-end from src/static/.

The `/api/index` prefix that the rewrite leaves on the request path is handled in
src/main.py, where the blueprints are mounted a second time under it. A WSGI
wrapper replacing `app.wsgi_app` was tried first and never ran here, even though it
behaves correctly under a normal server.
"""

import os
import sys

# Put the project root on the path so `src.*` and `prompts/` resolve inside the
# function bundle. Must happen before importing src.main.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app  # noqa: E402  (import has to follow the sys.path fix)

# Vercel picks up this name as the handler.
__all__ = ['app']
