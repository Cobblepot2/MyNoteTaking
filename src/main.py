import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.note import note_bp
from src.models.note import Note

# Load .env for local development. On Vercel the vars come from the platform.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Enable CORS for all routes
CORS(app)

# register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(note_bp, url_prefix='/api')
# Configure the database. Supabase (Postgres) in the cloud via DATABASE_URL,
# local SQLite file as a fallback so the app still runs without any setup.
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Supabase hands out either `postgres://` or `postgresql://`; SQLAlchemy needs
    # the driver spelled out explicitly.
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
    db_uri = DATABASE_URL
    # Log the host only - never the password.
    print(f"[db] Supabase Postgres @ {db_uri.rsplit('@', 1)[-1].split('/')[0]}")
else:
    ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DB_PATH = os.path.join(ROOT_DIR, 'database', 'app.db')
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db_uri = f"sqlite:///{DB_PATH}"
    print('[db] DATABASE_URL not set - falling back to local SQLite')

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Supabase drops idle connections. Without pre_ping/recycle, the first query after
# a cold start - i.e. every request on Vercel - fails on a stale connection.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
db.init_app(app)
with app.app_context():
    # Tables already exist in Supabase. On Vercel this runs on every cold start, so
    # keep a transient database blip from crashing the whole function at import time.
    try:
        db.create_all()
    except Exception as exc:
        app.logger.warning('Skipping db.create_all(): %s', exc)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
