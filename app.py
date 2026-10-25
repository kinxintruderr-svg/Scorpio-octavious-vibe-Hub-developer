
import os

from flask import Flask, jsonify, request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

app = Flask(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if FRONTEND_ORIGIN and origin == FRONTEND_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )
    return response


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "SOV Develop Hub API",
        "status": "running"
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "SOV Develop Hub API",
        "status": "healthy"
    }), 200


@app.route("/api/me", methods=["GET"])
def current_user():
    if not GOOGLE_CLIENT_ID:
        return jsonify({
            "error": "GOOGLE_CLIENT_ID is not configured in Render."
        }), 503

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return jsonify({"error": "Google ID token required."}), 401

    token = authorization.split(" ", 1)[1].strip()

    try:
        user = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        return jsonify({"error": "Invalid or expired Google token."}), 401
    except Exception:
        app.logger.exception("Google token verification failed")
        return jsonify({"error": "Google verification unavailable."}), 503

    if not user.get("email_verified"):
        return jsonify({"error": "Verified Google email required."}), 403

    email = user.get("email", "").strip().lower()

    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.get("sub"),
            "email": email,
            "name": user.get("name", "")
        },
        "is_admin": bool(ADMIN_EMAIL) and email == ADMIN_EMAIL
    }), 200


@app.route("/api/admin/check", methods=["GET"])
def admin_check():
    result = current_user()

    if isinstance(result, tuple):
        response, status = result
        if status != 200:
            return response, status

    # Verify the token again to enforce admin authorization on this route.
    if not GOOGLE_CLIENT_ID or not ADMIN_EMAIL:
        return jsonify({
            "error": "Google client ID or admin email is not configured."
        }), 503

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return jsonify({"error": "Google ID token required."}), 401

    try:
        user = id_token.verify_oauth2_token(
            authorization.split(" ", 1)[1].strip(),
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except Exception:
        return jsonify({"error": "Invalid Google ID token."}), 401

    email = user.get("email", "").strip().lower()
    if not user.get("email_verified") or email != ADMIN_EMAIL:
        return jsonify({"error": "Admin access required."}), 403

    return jsonify({"authorized": True, "email": email}), 200


@app.route("/api/apps", methods=["GET"])
def list_apps():
    # Marketplace storage and public APK downloads come next.
    return jsonify({
        "apps": [],
        "message": "Marketplace has no published apps yet."
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        debug=False
    )
