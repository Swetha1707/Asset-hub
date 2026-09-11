from flask import Blueprint, render_template, jsonify
from database.db import query_all, query_one
from utils.security import login_required, current_user, get_user_permissions

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_home():
    user = current_user()
    perms = get_user_permissions(user)
    return render_template("dashboard.html", user=user, perms=perms)


@dashboard_bp.route("/api/dashboard/summary")
@login_required
def dashboard_summary():
    total_assets = query_one("SELECT COUNT(*) c FROM assets WHERE is_deleted=0")["c"]
    assigned = query_one("SELECT COUNT(*) c FROM assets WHERE status='ASSIGNED' AND is_deleted=0")["c"]
    available = query_one("SELECT COUNT(*) c FROM assets WHERE status='AVAILABLE' AND is_deleted=0")["c"]
    maintenance = query_one("SELECT COUNT(*) c FROM assets WHERE status='UNDER_MAINTENANCE' AND is_deleted=0")["c"]
    retired = query_one("SELECT COUNT(*) c FROM assets WHERE status IN ('RETIRED','DISPOSED') AND is_deleted=0")["c"]
    total_employees = query_one("SELECT COUNT(*) c FROM employees WHERE status='ACTIVE'")["c"]
    pending_requests = query_one("SELECT COUNT(*) c FROM asset_requests WHERE status='PENDING'")["c"]
    active_licenses = query_one("SELECT COUNT(*) c FROM licenses WHERE expiry_date >= CURDATE()")["c"]
    expiring_licenses = query_one(
        "SELECT COUNT(*) c FROM licenses WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)"
    )["c"]
    total_value = query_one("SELECT COALESCE(SUM(current_value),0) v FROM assets WHERE is_deleted=0")["v"]

    by_category = query_all(
        """SELECT ac.name AS label, COUNT(a.id) AS value
           FROM assets a JOIN asset_categories ac ON a.category_id = ac.id
           WHERE a.is_deleted=0 GROUP BY ac.name ORDER BY value DESC"""
    )
    by_department = query_all(
        """SELECT d.name AS label, COUNT(a.id) AS value
           FROM assets a JOIN departments d ON a.department_id = d.id
           WHERE a.is_deleted=0 GROUP BY d.name ORDER BY value DESC"""
    )
    by_status = query_all(
        "SELECT status AS label, COUNT(*) AS value FROM assets WHERE is_deleted=0 GROUP BY status"
    )
    value_by_department = query_all(
        """SELECT d.name AS label, COALESCE(SUM(a.current_value),0) AS value
           FROM assets a JOIN departments d ON a.department_id = d.id
           WHERE a.is_deleted=0 GROUP BY d.name ORDER BY value DESC"""
    )
    maintenance_overview = query_all(
        "SELECT status AS label, COUNT(*) AS value FROM maintenance GROUP BY status"
    )
    license_expiry = query_all(
        """SELECT software_name AS label, DATEDIFF(expiry_date, CURDATE()) AS value
           FROM licenses ORDER BY expiry_date ASC LIMIT 6"""
    )
    monthly_requests = query_all(
    """SELECT DATE_FORMAT(created_at, '%%b %%Y') AS label, COUNT(*) AS value
       FROM asset_requests
       GROUP BY DATE_FORMAT(created_at, '%%b %%Y'),
                YEAR(created_at),
                MONTH(created_at)
       ORDER BY YEAR(created_at) DESC, MONTH(created_at) DESC
       LIMIT 6"""
)

    # AI-generated insight cards (rule based over real data)
    insights = []
    if expiring_licenses:
        insights.append({"icon": "⚠️", "text": f"{expiring_licenses} license(s) expire within 30 days."})
    repeated_maint = query_one(
        """SELECT COUNT(*) c FROM (
             SELECT asset_id FROM maintenance GROUP BY asset_id HAVING COUNT(*) >= 2
           ) t"""
    )["c"]
    if repeated_maint:
        insights.append({"icon": "🔧", "text": f"{repeated_maint} asset(s) have repeated maintenance records."})
    top_dept = query_one(
        """SELECT d.name, COALESCE(SUM(a.current_value),0) v FROM assets a
           JOIN departments d ON a.department_id=d.id WHERE a.is_deleted=0
           GROUP BY d.name ORDER BY v DESC LIMIT 1"""
    )
    if top_dept and top_dept["v"]:
        insights.append({"icon": "💰", "text": f"{top_dept['name']} owns the highest total asset value (₹{int(top_dept['v']):,})."})
    unassigned = query_one("SELECT COUNT(*) c FROM assets WHERE status='AVAILABLE' AND is_deleted=0")["c"]
    if unassigned:
        insights.append({"icon": "📦", "text": f"{unassigned} asset(s) are currently unassigned."})

    return jsonify({
        "cards": {
            "total_assets": total_assets, "assigned": assigned, "available": available,
            "maintenance": maintenance, "retired": retired, "total_employees": total_employees,
            "pending_requests": pending_requests, "active_licenses": active_licenses,
            "expiring_licenses": expiring_licenses, "total_value": float(total_value),
        },
        "charts": {
            "by_category": by_category, "by_department": by_department, "by_status": by_status,
            "value_by_department": value_by_department, "maintenance_overview": maintenance_overview,
            "license_expiry": license_expiry, "monthly_requests": list(reversed(monthly_requests)),
        },
        "insights": insights,
    })
