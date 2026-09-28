import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory
)
from flask_cors import CORS
import jwt


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "sov_dev_hub.db")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

APK_DIR = os.path.join(UPLOAD_DIR, "apks")

ICON_DIR = os.path.join(UPLOAD_DIR, "icons")

SCREENSHOT_DIR = os.path.join(UPLOAD_DIR, "screenshots")


JWT_SECRET = os.environ.get(
    "SOV_DEV_HUB_JWT_SECRET",
    "CHANGE_THIS_SECRET_BEFORE_PRODUCTION"
)


ADMIN_KEY = os.environ.get(
    "SOV_DEV_HUB_ADMIN_KEY",
    "CHANGE_THIS_ADMIN_KEY"
)


ALLOWED_APK_EXTENSIONS = {".apk"}

ALLOWED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
}


MAX_APK_SIZE = 200 * 1024 * 1024


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

CORS(app)


app.config["MAX_CONTENT_LENGTH"] = MAX_APK_SIZE


# ============================================================
# DIRECTORIES
# ============================================================

os.makedirs(APK_DIR, exist_ok=True)

os.makedirs(ICON_DIR, exist_ok=True)

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def get_db():

    db = sqlite3.connect(DATABASE)

    db.row_factory = sqlite3.Row

    return db


def init_database():

    db = get_db()

    db.executescript("""
    
    CREATE TABLE IF NOT EXISTS developers (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password_hash TEXT NOT NULL,

        display_name TEXT NOT NULL,

        created_at TEXT NOT NULL

    );


    CREATE TABLE IF NOT EXISTS apps (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        developer_id INTEGER NOT NULL,

        name TEXT NOT NULL,

        description TEXT NOT NULL,

        category TEXT NOT NULL,

        version TEXT NOT NULL,

        apk_filename TEXT NOT NULL,

        icon_filename TEXT,

        status TEXT NOT NULL DEFAULT 'pending',

        downloads INTEGER NOT NULL DEFAULT 0,

        created_at TEXT NOT NULL,

        updated_at TEXT NOT NULL,

        FOREIGN KEY(developer_id)
        REFERENCES developers(id)

    );


    CREATE TABLE IF NOT EXISTS app_screenshots (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        app_id INTEGER NOT NULL,

        filename TEXT NOT NULL,

        created_at TEXT NOT NULL,

        FOREIGN KEY(app_id)
        REFERENCES apps(id)

    );


    CREATE INDEX IF NOT EXISTS
    idx_apps_status
    ON apps(status);


    CREATE INDEX IF NOT EXISTS
    idx_apps_category
    ON apps(category);


    """)

    db.commit()

    db.close()


init_database()


# ============================================================
# PASSWORDS
# ============================================================

def hash_password(password):

    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120000
    )

    return salt + ":" + digest.hex()


def verify_password(password, stored):

    try:

        salt, old_digest = stored.split(":", 1)

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            120000
        )

        return secrets.compare_digest(
            digest.hex(),
            old_digest
        )

    except Exception:

        return False


# ============================================================
# JWT
# ============================================================

def create_token(developer):

    payload = {

        "developer_id": developer["id"],

        "username": developer["username"],

        "exp": (
            datetime.now(timezone.utc)
        ).timestamp() + 60 * 60 * 24 * 7

    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm="HS256"
    )


def developer_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        header = request.headers.get(
            "Authorization",
            ""
        )

        if not header.startswith("Bearer "):

            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401


        token = header.split(
            " ",
            1
        )[1]


        try:

            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )

        except jwt.ExpiredSignatureError:

            return jsonify({
                "success": False,
                "error": "Token expired"
            }), 401

        except jwt.InvalidTokenError:

            return jsonify({
                "success": False,
                "error": "Invalid token"
            }), 401


        db = get_db()

        developer = db.execute(
            """
            SELECT *
            FROM developers
            WHERE id = ?
            """,
            (payload["developer_id"],)
        ).fetchone()

        db.close()


        if not developer:

            return jsonify({
                "success": False,
                "error": "Developer not found"
            }), 401


        return function(
            developer,
            *args,
            **kwargs
        )


    return wrapper


# ============================================================
# HELPERS
# ============================================================

def allowed_file(filename, extensions):

    if not filename:

        return False

    extension = os.path.splitext(
        filename
    )[1].lower()

    return extension in extensions


def safe_filename(filename):

    filename = os.path.basename(filename)

    return "".join(
        character
        for character in filename
        if character.isalnum()
        or character in "._-"
    )


def now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")

def home():

    return jsonify({

        "success": True,

        "service": "SOV Dev Hub API",

        "version": "1.0.0",

        "status": "online"

    })


# ============================================================
# DEVELOPER REGISTER
# ============================================================

@app.post("/api/developers/register")

def register():

    data = request.get_json(
        silent=True
    ) or {}


    username = str(
        data.get("username", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    display_name = str(
        data.get("display_name", username)
    ).strip()


    if not username:

        return jsonify({
            "success": False,
            "error": "Username is required"
        }), 400


    if not email:

        return jsonify({
            "success": False,
            "error": "Email is required"
        }), 400


    if len(password) < 8:

        return jsonify({
            "success": False,
            "error":
            "Password must contain at least 8 characters"
        }), 400


    db = get_db()


    existing = db.execute(
        """
        SELECT id
        FROM developers
        WHERE username = ?
        OR email = ?
        """,
        (
            username,
            email
        )
    ).fetchone()


    if existing:

        db.close()

        return jsonify({
            "success": False,
            "error":
            "Username or email already exists"
        }), 409


    cursor = db.execute(
        """
        INSERT INTO developers
        (
            username,
            email,
            password_hash,
            display_name,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            username,
            email,
            hash_password(password),
            display_name,
            now()
        )
    )


    db.commit()


    developer_id = cursor.lastrowid


    developer = db.execute(
        """
        SELECT *
        FROM developers
        WHERE id = ?
        """,
        (developer_id,)
    ).fetchone()


    db.close()


    return jsonify({

        "success": True,

        "message": "Developer account created",

        "token": create_token(
            developer
        ),

        "developer": {

            "id": developer["id"],

            "username": developer["username"],

            "email": developer["email"],

            "display_name":
                developer["display_name"]

        }

    }), 201


# ============================================================
# DEVELOPER LOGIN
# ============================================================

@app.post("/api/developers/login")

def login():

    data = request.get_json(
        silent=True
    ) or {}


    username_or_email = str(
        data.get(
            "username_or_email",
            ""
        )
    ).strip().lower()


    password = str(
        data.get(
            "password",
            ""
        )
    )


    db = get_db()


    developer = db.execute(
        """
        SELECT *
        FROM developers
        WHERE lower(username) = ?
        OR lower(email) = ?
        """,
        (
            username_or_email,
            username_or_email
        )
    ).fetchone()


    db.close()


    if not developer:

        return jsonify({
            "success": False,
            "error": "Invalid login details"
        }), 401


    if not verify_password(
        password,
        developer["password_hash"]
    ):

        return jsonify({
            "success": False,
            "error": "Invalid login details"
        }), 401


    return jsonify({

        "success": True,

        "token": create_token(
            developer
        ),

        "developer": {

            "id": developer["id"],

            "username":
                developer["username"],

            "email":
                developer["email"],

            "display_name":
                developer["display_name"]

        }

    })


# ============================================================
# MY DEVELOPER PROFILE
# ============================================================

@app.get("/api/developers/me")

@developer_required

def developer_me(developer):

    return jsonify({

        "success": True,

        "developer": {

            "id": developer["id"],

            "username":
                developer["username"],

            "email":
                developer["email"],

            "display_name":
                developer["display_name"],

            "created_at":
                developer["created_at"]

        }

    })


# ============================================================
# UPLOAD APP
# ============================================================

@app.post("/api/apps")

@developer_required

def upload_app(developer):

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    version = request.form.get(
        "version",
        ""
    ).strip()


    apk = request.files.get(
        "apk"
    )

    icon = request.files.get(
        "icon"
    )


    if not name:

        return jsonify({
            "success": False,
            "error": "App name is required"
        }), 400


    if not description:

        return jsonify({
            "success": False,
            "error": "Description is required"
        }), 400


    if not category:

        return jsonify({
            "success": False,
            "error": "Category is required"
        }), 400


    if not version:

        return jsonify({
            "success": False,
            "error": "Version is required"
        }), 400


    if not apk:

        return jsonify({
            "success": False,
            "error": "APK file is required"
        }), 400


    if not allowed_file(
        apk.filename,
        ALLOWED_APK_EXTENSIONS
    ):

        return jsonify({
            "success": False,
            "error": "Only APK files are allowed"
        }), 400


    # Generate server-side filename.
    # Never trust the original filename.
    apk_filename = (
        secrets.token_hex(16)
        + ".apk"
    )


    apk_path = os.path.join(
        APK_DIR,
        apk_filename
    )


    apk.save(apk_path)


    icon_filename = None


    if icon:

        if not allowed_file(
            icon.filename,
            ALLOWED_IMAGE_EXTENSIONS
        ):

            os.remove(apk_path)

            return jsonify({
                "success": False,
                "error":
                "Unsupported icon format"
            }), 400


        icon_extension = os.path.splitext(
            icon.filename
        )[1].lower()


        icon_filename = (
            secrets.token_hex(16)
            + icon_extension
        )


        icon.save(
            os.path.join(
                ICON_DIR,
                icon_filename
            )
        )


    timestamp = now()


    db = get_db()


    cursor = db.execute(
        """
        INSERT INTO apps
        (
            developer_id,
            name,
            description,
            category,
            version,
            apk_filename,
            icon_filename,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            developer["id"],
            name,
            description,
            category,
            version,
            apk_filename,
            icon_filename,
            "pending",
            timestamp,
            timestamp
        )
    )


    db.commit()


    app_id = cursor.lastrowid

    db.close()


    return jsonify({

        "success": True,

        "message":
            "App submitted for admin review",

        "app_id": app_id,

        "status": "pending"

    }), 201


# ============================================================
# PUBLIC APPS
# ============================================================

@app.get("/api/apps")

def public_apps():

    category = request.args.get(
        "category",
        ""
    ).strip()

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()


    query = """
        SELECT
            apps.id,
            apps.name,
            apps.description,
            apps.category,
            apps.version,
            apps.icon_filename,
            apps.downloads,
            apps.created_at,
            developers.username AS developer
        FROM apps
        JOIN developers
        ON developers.id = apps.developer_id
        WHERE apps.status = 'approved'
    """


    params = []


    if category:

        query += """
            AND apps.category = ?
        """

        params.append(category)


    if search:

        query += """
            AND (
                apps.name LIKE ?
                OR apps.description LIKE ?
                OR developers.username LIKE ?
            )
        """

        search_value = (
            "%"
            + search
            + "%"
        )

        params.extend([
            search_value,
            search_value,
            search_value
        ])


    query += """
        ORDER BY apps.created_at DESC
    """


    rows = db.execute(
        query,
        params
    ).fetchall()


    db.close()


    return jsonify({

        "success": True,

        "apps": [

            {

                "id": row["id"],

                "name": row["name"],

                "description":
                    row["description"],

                "category":
                    row["category"],

                "version":
                    row["version"],

                "developer":
                    row["developer"],

                "downloads":
                    row["downloads"],

                "icon":
                    (
                        "/api/icons/"
                        + row["icon_filename"]
                    )
                    if row["icon_filename"]
                    else None

            }

            for row in rows

        ]

    })


# ============================================================
# APP DETAILS
# ============================================================

@app.get("/api/apps/<int:app_id>")

def app_details(app_id):

    db = get_db()


    row = db.execute(
        """
        SELECT
            apps.*,
            developers.username AS developer,
            developers.display_name
                AS developer_name
        FROM apps
        JOIN developers
        ON developers.id = apps.developer_id
        WHERE apps.id = ?
        AND apps.status = 'approved'
        """,
        (app_id,)
    ).fetchone()


    db.close()


    if not row:

        return jsonify({
            "success": False,
            "error": "App not found"
        }), 404


    return jsonify({

        "success": True,

        "app": {

            "id": row["id"],

            "name": row["name"],

            "description":
                row["description"],

            "category":
                row["category"],

            "version":
                row["version"],

            "developer":
                row["developer"],

            "developer_name":
                row["developer_name"],

            "downloads":
                row["downloads"],

            "icon":
                (
                    "/api/icons/"
                    + row["icon_filename"]
                )
                if row["icon_filename"]
                else None

        }

    })


# ============================================================
# DOWNLOAD APK
# ============================================================

@app.get("/api/apps/<int:app_id>/download")

def download_app(app_id):

    db = get_db()


    row = db.execute(
        """
        SELECT *
        FROM apps
        WHERE id = ?
        AND status = 'approved'
        """,
        (app_id,)
    ).fetchone()


    if not row:

        db.close()

        return jsonify({
            "success": False,
            "error": "App not found"
        }), 404


    db.execute(
        """
        UPDATE apps
        SET downloads = downloads + 1
        WHERE id = ?
        """,
        (app_id,)
    )


    db.commit()

    db.close()


    return send_from_directory(
        APK_DIR,
        row["apk_filename"],
        as_attachment=True,
        download_name=(
            safe_filename(
                row["name"]
            )
            + "-"
            + row["version"]
            + ".apk"
        )
    )


# ============================================================
# ICON
# ============================================================

@app.get("/api/icons/<filename>")

def icon(filename):

    return send_from_directory(
        ICON_DIR,
        safe_filename(filename)
    )


# ============================================================
# DEVELOPER'S APPS
# ============================================================

@app.get("/api/developers/my-apps")

@developer_required

def my_apps(developer):

    db = get_db()


    rows = db.execute(
        """
        SELECT *
        FROM apps
        WHERE developer_id = ?
        ORDER BY created_at DESC
        """,
        (developer["id"],)
    ).fetchall()


    db.close()


    return jsonify({

        "success": True,

        "apps": [

            {

                "id": row["id"],

                "name": row["name"],

                "category":
                    row["category"],

                "version":
                    row["version"],

                "status":
                    row["status"],

                "downloads":
                    row["downloads"],

                "created_at":
                    row["created_at"],

                "updated_at":
                    row["updated_at"]

            }

            for row in rows

        ]

    })

# ============================================================
# ADMIN AUTH
# ============================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        supplied = request.headers.get(
            "X-Admin-Key",
            ""
        )


        if not supplied:

            return jsonify({
                "success": False,
                "error": "Admin authentication required"
            }), 401


        if not secrets.compare_digest(
            supplied,
            ADMIN_KEY
        ):

            return jsonify({
                "success": False,
                "error": "Invalid admin key"
            }), 403


        return function(
            *args,
            **kwargs
        )


    return wrapper

