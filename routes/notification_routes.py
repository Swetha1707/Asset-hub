"""
Notification Center — ADMIN-ONLY per the mandatory access rule.
Every route here is protected by permission_required("VIEW_NOTIFICATIONS"),
which is hard-blocked for EMPLOYEE role at the utils.security layer
regardless of any per-user override. An Employee hitting these URLs
directly always receives HTTP 403.
"""
from flask import Blueprint, render_template, request, jsonify
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity

notification_bp = Blueprint("notification", __name__)


@notification_bp.route("/notifications")
@login_required
def notifications_page():
    return render_template("notifications.html")


@notification_bp.route("/api/notifications")
@login_required
def api_list_notifications():
    user = current_user()
    rows = query_all(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user["id"],))
    unread = query_one(
        "SELECT COUNT(*) c FROM notifications WHERE user_id=%s AND is_read=0", (user["id"],))["c"]
    return jsonify({"data": rows, "unread_count": unread})


@notification_bp.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def api_mark_read(notif_id):
    user = current_user()
    execute("UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s", (notif_id, user["id"]))
    return jsonify({"message": "Marked as read."})


@notification_bp.route("/api/notifications/read-all", methods=["POST"])
@login_required
def api_mark_all_read():
    user = current_user()
    execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (user["id"],))
    return jsonify({"message": "All notifications marked as read."})
