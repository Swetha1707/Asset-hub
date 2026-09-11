"""
Central authentication / authorization / audit-log helpers.
Every route in the app must go through these decorators — permissions are
NEVER enforced only by hiding buttons in the frontend.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify, abort
from database.db import query_all, query_one, execute

# Permissions that an EMPLOYEE role must never have, no matter what —
# hard server-side block per the "IMPORTANT ACCESS RULE" in the spec.
EMPLOYEE_FORBIDDEN_PERMISSIONS = {
    "MANAGE_ADMINS"
}


def current_user():
    if "user_id" not in session:
        return None
    return query_one(
        """SELECT u.*, r.name AS role_name
           FROM users u JOIN roles r ON u.role_id = r.id
           WHERE u.id = %s AND u.is_active = 1""",
        (session["user_id"],),
    )


def get_user_permissions(user):
    """Union of role-level permissions and per-user overrides,
    with a hard server-side block on employee-forbidden permissions."""
    if not user:
        return set()
    role_perms = query_all(
        """SELECT p.code FROM role_permissions rp
           JOIN permissions p ON rp.permission_id = p.id
           WHERE rp.role_id = %s""",
        (user["role_id"],),
    )
    user_perms = query_all(
        """SELECT p.code FROM user_permissions up
           JOIN permissions p ON up.permission_id = p.id
           WHERE up.user_id = %s""",
        (user["id"],),
    )
    perms = {p["code"] for p in role_perms} | {p["code"] for p in user_perms}

    if user["role_name"] == "EMPLOYEE":
        perms -= EMPLOYEE_FORBIDDEN_PERMISSIONS

    return perms


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped


def permission_required(permission_code):
    """Hard server-side permission check — returns 403 for anyone lacking it,
    including any Employee attempting AI Assistant / Notifications URLs directly."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login"))

            perms = get_user_permissions(user)
            if permission_code not in perms:
                log_activity(user, "ACCESS_DENIED", "SECURITY",
                             f"Denied access to {request.path} (missing {permission_code})",
                             status="DENIED")
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden: insufficient permissions"}), 403
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def role_required(*role_names):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("auth.login"))
            if user["role_name"] not in role_names:
                log_activity(user, "ACCESS_DENIED", "SECURITY",
                             f"Denied access to {request.path} (role {user['role_name']})",
                             status="DENIED")
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden"}), 403
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def log_activity(user, action, module, description="", status="SUCCESS"):
    """Write an entry to activity_logs. Never raises — logging failures
    must not break the primary request."""
    try:
        execute(
            """INSERT INTO activity_logs (user_id, username, action, module, description, ip_address, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                user["id"] if user else None,
                user["username"] if user else "anonymous",
                action,
                module,
                description,
                request.remote_addr if request else None,
                status,
            ),
        )
    except Exception:
        pass
