from flask import Blueprint, render_template, request, jsonify
from werkzeug.security import generate_password_hash
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, role_required, current_user, log_activity

admin_bp = Blueprint("admin", __name__)

# Permissions automatically granted to any newly created ADMIN account,
# per the "IMPORTANT ACCESS RULE" in the spec.
NEW_ADMIN_DEFAULT_PERMISSIONS = ["USE_AI_ASSISTANT", "VIEW_NOTIFICATIONS"]


@admin_bp.route("/admin/management")
@login_required
@role_required("SUPER_ADMIN", "ADMIN")
@permission_required("MANAGE_ADMINS")
def admin_management_page():
    return render_template("admin_management.html")


@admin_bp.route("/api/admin/admins")
@login_required
@permission_required("MANAGE_ADMINS")
def api_list_admins():
    rows = query_all(
        """SELECT u.id, u.full_name, u.username, u.email, u.is_active, r.name AS role_name,
                  u.created_at
           FROM users u JOIN roles r ON u.role_id = r.id
           WHERE r.name IN ('ADMIN','SUPER_ADMIN') ORDER BY u.created_at DESC""")
    return jsonify({"data": rows})


@admin_bp.route("/api/admin/admins", methods=["POST"])
@login_required
@permission_required("MANAGE_ADMINS")
def api_create_admin():
    user = current_user()
    d = request.json
    for f in ["full_name", "username", "email", "password"]:
        if not d.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400
    if len(d["password"]) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if query_one("SELECT id FROM users WHERE username=%s", (d["username"],)):
        return jsonify({"error": "Username already taken"}), 400
    if query_one("SELECT id FROM users WHERE email=%s", (d["email"],)):
        return jsonify({"error": "Email already registered"}), 400

    admin_role = query_one("SELECT id FROM roles WHERE name='ADMIN'")
    pw_hash = generate_password_hash(d["password"])
    result = execute(
        """INSERT INTO users (full_name, username, email, phone, password_hash, role_id, is_active)
           VALUES (%s,%s,%s,%s,%s,%s,1)""",
        (d["full_name"], d["username"], d["email"], d.get("phone"), pw_hash, admin_role["id"]),
    )
    new_admin_id = result["lastrowid"]

    # Auto-grant AI Assistant + Notifications per the mandatory access rule.
    for code in NEW_ADMIN_DEFAULT_PERMISSIONS:
        perm = query_one("SELECT id FROM permissions WHERE code=%s", (code,))
        if perm:
            execute("INSERT IGNORE INTO user_permissions (user_id, permission_id) VALUES (%s,%s)",
                    (new_admin_id, perm["id"]))

    # Grant any additional explicitly requested permissions
    for code in d.get("permissions", []):
        perm = query_one("SELECT id FROM permissions WHERE code=%s", (code,))
        if perm:
            execute("INSERT IGNORE INTO user_permissions (user_id, permission_id) VALUES (%s,%s)",
                    (new_admin_id, perm["id"]))

    log_activity(user, "ADMIN_CREATED", "ADMIN_MANAGEMENT", f"Created admin account '{d['username']}'")
    return jsonify({"message": "Administrator created successfully.", "id": new_admin_id}), 201


@admin_bp.route("/api/admin/admins/<int:admin_id>/status", methods=["POST"])
@login_required
@permission_required("MANAGE_ADMINS")
def api_toggle_admin_status(admin_id):
    user = current_user()
    d = request.json
    execute("UPDATE users SET is_active=%s WHERE id=%s", (1 if d.get("is_active") else 0, admin_id))
    log_activity(user, "ADMIN_STATUS_CHANGED", "ADMIN_MANAGEMENT",
                 f"{'Activated' if d.get('is_active') else 'Deactivated'} admin #{admin_id}")
    return jsonify({"message": "Administrator status updated."})


@admin_bp.route("/api/admin/admins/<int:admin_id>/permissions", methods=["GET", "POST"])
@login_required
@permission_required("MANAGE_ADMINS")
def api_admin_permissions(admin_id):
    if request.method == "GET":
        all_perms = query_all("SELECT * FROM permissions ORDER BY label")
        granted = {r["code"] for r in query_all(
            """SELECT p.code FROM user_permissions up JOIN permissions p ON up.permission_id=p.id
               WHERE up.user_id=%s""", (admin_id,))}
        role_perms = {r["code"] for r in query_all(
            """SELECT p.code FROM role_permissions rp JOIN permissions p ON rp.permission_id=p.id
               JOIN users u ON u.role_id = rp.role_id WHERE u.id=%s""", (admin_id,))}
        return jsonify({"all": all_perms, "granted": list(granted | role_perms), "override_only": list(granted)})

    user = current_user()
    d = request.json
    codes = d.get("permissions", [])
    execute("DELETE FROM user_permissions WHERE user_id=%s", (admin_id,))
    for code in codes:
        perm = query_one("SELECT id FROM permissions WHERE code=%s", (code,))
        if perm:
            execute("INSERT IGNORE INTO user_permissions (user_id, permission_id) VALUES (%s,%s)",
                    (admin_id, perm["id"]))
    log_activity(user, "ADMIN_PERMISSIONS_CHANGED", "ADMIN_MANAGEMENT", f"Updated permissions for admin #{admin_id}")
    return jsonify({"message": "Permissions updated successfully."})


@admin_bp.route("/api/admin/admins/<int:admin_id>/activity")
@login_required
@permission_required("MANAGE_ADMINS")
def api_admin_activity(admin_id):
    rows = query_all(
        "SELECT * FROM activity_logs WHERE user_id=%s ORDER BY created_at DESC LIMIT 100", (admin_id,))
    return jsonify({"data": rows})


# ---------------- Activity Logs (system-wide) ----------------
@admin_bp.route("/activity-logs")
@login_required
@permission_required("VIEW_ACTIVITY_LOGS")
def activity_logs_page():
    return render_template("activity_logs.html")


@admin_bp.route("/api/activity-logs")
@login_required
@permission_required("VIEW_ACTIVITY_LOGS")
def api_activity_logs():
    where = ["1=1"]; params = []
    if request.args.get("username"):
        where.append("username LIKE %s"); params.append(f"%{request.args['username']}%")
    if request.args.get("action"):
        where.append("action = %s"); params.append(request.args["action"])
    if request.args.get("module"):
        where.append("module = %s"); params.append(request.args["module"])
    if request.args.get("date_from"):
        where.append("created_at >= %s"); params.append(request.args["date_from"])
    if request.args.get("date_to"):
        where.append("created_at <= %s"); params.append(request.args["date_to"] + " 23:59:59")
    if request.args.get("q"):
        where.append("(description LIKE %s OR username LIKE %s)")
        like = f"%{request.args['q']}%"; params += [like, like]

    rows = query_all(
        f"SELECT * FROM activity_logs WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 500", params)
    return jsonify({"data": rows})
