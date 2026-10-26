
import os
import re
import uuid
import sqlite3
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
ADMIN_EMAIL = os.environ.get(
    "ADMIN_EMAIL", "kinxintruder@gmail.com"
).strip().lower()

DATABASE_PATH = os.environ.get("DATABASE_PATH", "sov_develop_hub.db")
UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", "uploads")).resolve()
MAX_APK_SIZE = 200 * 1024 * 1024  # 200 MB

app.config["MAX_CONTENT_LENGTH"] = MAX_APK_SIZE
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Set FRONTEND_ORIGIN to your exact deployed Develop Hub website origin.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "").strip()
allowed_origins = [FRONTEND_ORIGIN] if FRONTEND_ORIGIN else []


CORS(
    app,
    resources={
        r"/api/*": {"origins": allowed_origins},
        r"/health": {"origins": allowed_origins},
    },
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
)



def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS apps (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            description TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'approved', 'rejected')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            app_id TEXT NOT NULL,
            user_email TEXT NOT NULL,
            user_name TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(app_id) REFERENCES apps(id) ON DELETE CASCADE,
            UNIQUE(app_id, user_email)
        );

        CREATE INDEX IF NOT EXISTS idx_apps_status
            ON apps(status);

        CREATE INDEX IF NOT EXISTS idx_reviews_app
            ON reviews(app_id);
    """)

    db.commit()
    db.close()


def error(message, status=400):
    return jsonify({"error": message}), status


def current_user():
    if hasattr(g, "user"):
        return g.user

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    if not token or not GOOGLE_CLIENT_ID:
        return None

    try:
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        email = claims.get("email", "").strip().lower()

        # Require Google's verified-email claim.
        if not email or claims.get("email_verified") is not True:
            return None

        g.user = {
            "email": email,
            "name": claims.get("name") or email.split("@")[0],
            "google_id": claims.get("sub"),
            "is_admin": email == ADMIN_EMAIL,
        }
        return g.user

    except Exception:
        return None


def require_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return error("Valid Google Sign-In is required.", 401)
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return error("Valid Google Sign-In is required.", 401)
        if not user["is_admin"]:
            return error("Administrator access required.", 403)
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def app_summary(row):
    db = get_db()
    rating = db.execute("""
        SELECT AVG(rating) AS average, COUNT(*) AS total
        FROM reviews WHERE app_id = ?
    """, (row["id"],)).fetchone()

    return {
        "id": row["id"],
        "name": row["name"],
        "version": row["version"],
        "description": row["description"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "rating": round(rating["average"] or 0, 1),
        "review_count": rating["total"],
        "download_url": (
            f"/api/apps/{row['id']}/download"
            if row["status"] == "approved"
            else None
        ),
    }


@app.get("/")
def index():
    return jsonify({
        "service": "SOV Develop Hub API",
        "status": "running",
    })


@app.get("/health")
def health():
    return jsonify({
        "service": "SOV Develop Hub API",
        "status": "running",
        "time": utc_now(),
    })


@app.get("/api/me")
@require_user
def me():
    return jsonify({
        "user": {
            "name": g.user["name"],
            "email": g.user["email"],
        },
        "is_admin": g.user["is_admin"],
    })


@app.get("/api/apps")
def list_apps():
    db = get_db()
    rows = db.execute("""
        SELECT * FROM apps
        WHERE status = 'approved'
        ORDER BY created_at DESC
    """).fetchall()

    return jsonify({
        "apps": [app_summary(row) for row in rows],
        "message": "No apps have been published yet."
        if not rows else None,
    })


@app.post("/api/apps")
@require_user
def submit_app():
    name = request.form.get("name", "").strip()
    version = request.form.get("version", "").strip()
    description = request.form.get("description", "").strip()
    apk = request.files.get("apk")

    if not name or len(name) > 100:
        return error("App name is required and must be at most 100 characters.")

    if not version or len(version) > 30:
        return error("A version is required and must be at most 30 characters.")

    if not description or len(description) > 5000:
        return error("Description is required and must be at most 5000 characters.")

    if not apk or not apk.filename:
        return error("Select an APK file.")

    original = secure_filename(apk.filename)
    if not original or not original.lower().endswith(".apk"):
        return error("Only .apk files are accepted.")

    app_id = str(uuid.uuid4())
    stored_filename = app_id + ".apk"
    destination = UPLOAD_FOLDER / stored_filename

    try:
        apk.save(destination)

        # Basic file signature check; this is not a complete APK security scan.
        with destination.open("rb") as file:
            if file.read(4) != b"PK\x03\x04":
                destination.unlink(missing_ok=True)
                return error("The uploaded file does not look like a valid APK archive.")

        now = utc_now()
        db = get_db()
        db.execute("""
            INSERT INTO apps (
                id, name, version, description, filename,
                original_filename, owner_email, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            app_id, name, version, description, stored_filename,
            original, g.user["email"], now, now,
        ))
        db.commit()

        return jsonify({
            "message": "App submitted for administrator review.",
            "app": {
                "id": app_id,
                "name": name,
                "version": version,
                "status": "pending",
            },
        }), 201

    except Exception:
        destination.unlink(missing_ok=True)
        app.logger.exception("App submission failed")
        return error("The app submission could not be saved.", 500)


@app.get("/api/apps/<app_id>/download")
def download_app(app_id):
    db = get_db()
    row = db.execute("""
        SELECT filename, original_filename
        FROM apps WHERE id = ? AND status = 'approved'
    """, (app_id,)).fetchone()

    if not row:
        return error("Published app not found.", 404)

    path = UPLOAD_FOLDER / row["filename"]
    if not path.is_file():
        return error(
            "APK file is unavailable. Check persistent file storage.", 503
        )

    return send_from_directory(
        str(UPLOAD_FOLDER),
        row["filename"],
        as_attachment=True,
        download_name=row["original_filename"],
    )


@app.get("/api/apps/<app_id>/reviews")
def get_reviews(app_id):
    db = get_db()
    published = db.execute("""
        SELECT id FROM apps WHERE id = ? AND status = 'approved'
    """, (app_id,)).fetchone()

    if not published:
        return error("Published app not found.", 404)

    rows = db.execute("""
        SELECT user_name, rating, text, created_at
        FROM reviews
        WHERE app_id = ?
        ORDER BY created_at DESC
    """, (app_id,)).fetchall()

    return jsonify({
        "reviews": [{
            "name": row["user_name"],
            "rating": row["rating"],
            "text": row["text"],
            "created_at": row["created_at"],
        } for row in rows]
    })


@app.post("/api/apps/<app_id>/reviews")
@require_user
def create_review(app_id):
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()

    try:
        rating = int(data.get("rating"))
    except (ValueError, TypeError):
        return error("Rating must be an integer from 1 to 5.")

    if rating < 1 or rating > 5:
        return error("Rating must be between 1 and 5.")

    if not text or len(text) > 2000:
        return error("Review text is required and must be at most 2000 characters.")

    db = get_db()
    published = db.execute("""
        SELECT id FROM apps WHERE id = ? AND status = 'approved'
    """, (app_id,)).fetchone()

    if not published:
        return error("Published app not found.", 404)

    review_id = str(uuid.uuid4())

    try:
        db.execute("""
            INSERT INTO reviews (
                id, app_id, user_email, user_name,
                rating, text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(app_id, user_email) DO UPDATE SET
                user_name = excluded.user_name,
                rating = excluded.rating,
                text = excluded.text,
                created_at = excluded.created_at
        """, (
            review_id, app_id, g.user["email"], g.user["name"],
            rating, text, utc_now(),
        ))
        db.commit()
    except sqlite3.Error:
        app.logger.exception("Review save failed")
        return error("Review could not be saved.", 500)

    return jsonify({"message": "Review saved successfully."}), 201


@app.get("/api/admin/apps/pending")
@require_admin
def pending_apps():
    db = get_db()
    rows = db.execute("""
        SELECT * FROM apps
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """).fetchall()

    return jsonify({"apps": [
        {
            **app_summary(row),
            "owner_email": row["owner_email"],
            "original_filename": row["original_filename"],
        }
        for row in rows
    ]})


def moderate_app(app_id, new_status):
    db = get_db()
    row = db.execute(
        "SELECT * FROM apps WHERE id = ?", (app_id,)
    ).fetchone()

    if not row:
        return error("App not found.", 404)

    if row["status"] != "pending":
        return error("Only pending apps can be approved or rejected.", 409)

    db.execute("""
        UPDATE apps SET status = ?, updated_at = ?
        WHERE id = ? AND status = 'pending'
    """, (new_status, utc_now(), app_id))
    db.commit()

    return jsonify({
        "message": f"App {new_status}.",
        "app_id": app_id,
        "status": new_status,
    })


@app.post("/api/admin/apps/<app_id>/approve")
@require_admin
def approve_app(app_id):
    return moderate_app(app_id, "approved")


@app.post("/api/admin/apps/<app_id>/reject")
@require_admin
def reject_app(app_id):
    return moderate_app(app_id, "rejected")


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "error": "Upload exceeds the configured 200 MB limit."
    }), 413


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "Internal server error."}), 500


# Initialize tables when the service starts.
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
