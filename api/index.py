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

from flask import jsonify, request  # noqa: E402

# TEMPORARY diagnostic route - remove once the Vercel routing is confirmed.
@app.route('/__diag')
def _vercel_diag():
    return jsonify({
        'path': request.path,
        'full_path': request.full_path,
        'url': request.url,
        'path_info': request.environ.get('PATH_INFO'),
        'script_name': request.environ.get('SCRIPT_NAME'),
        'headers': dict(request.headers),
    })


# Vercel picks up this name as the handler.
__all__ = ['app']
