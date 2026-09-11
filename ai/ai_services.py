"""
AI Services layer: a fixed catalogue of pre-validated, parameterized,
READ-ONLY database operations that the AI assistant is allowed to call.

The assistant NEVER builds or executes raw SQL from user text. It only
selects one of these functions (an "intent") and passes safe, validated
arguments. This is the enforcement boundary described in the spec:
"NEVER allow the AI to execute arbitrary SQL supplied directly by the user."
"""
from database.db import query_all, query_one


def count_assets_by_category_and_status(category_name=None, status="AVAILABLE"):
    where = ["a.is_deleted=0", "a.status=%s"]
    params = [status]
    if category_name:
        singular = category_name[:-1] if category_name.endswith("s") else category_name
        where.append("(ac.name LIKE %s OR ac.name LIKE %s)")
        params += [f"%{category_name}%", f"%{singular}%"]
    sql = f"""SELECT COUNT(*) c FROM assets a
              LEFT JOIN asset_categories ac ON a.category_id = ac.id
              WHERE {' AND '.join(where)}"""
    return query_one(sql, params)["c"]


def assets_by_department(department_name):
    return query_all(
        """SELECT a.asset_code, a.name, a.status, e.name AS assigned_to
           FROM assets a
           JOIN departments d ON a.department_id = d.id
           LEFT JOIN employees e ON a.assigned_employee_id = e.id
           WHERE d.name LIKE %s AND a.is_deleted = 0""",
        (f"%{department_name}%",),
    )


def who_has_asset(asset_code):
    return query_one(
        """SELECT a.asset_code, a.name, a.status, e.name AS assigned_to, d.name AS department
           FROM assets a
           LEFT JOIN employees e ON a.assigned_employee_id = e.id
           LEFT JOIN departments d ON a.department_id = d.id
           WHERE a.asset_code = %s AND a.is_deleted = 0""",
        (asset_code,),
    )


def pending_maintenance():
    return query_all(
        """SELECT a.asset_code, a.name, m.problem, m.status, m.expected_completion
           FROM maintenance m JOIN assets a ON m.asset_id = a.id
           WHERE m.status IN ('SCHEDULED','IN_PROGRESS') ORDER BY m.start_date""")


def licenses_expiring(days=30):
    return query_all(
        """SELECT software_name, expiry_date, vendor, renewal_status
           FROM licenses
           WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
           ORDER BY expiry_date""",
        (days,),
    )


def licenses_needing_renewal():
    return query_all(
        "SELECT software_name, expiry_date, renewal_status FROM licenses WHERE renewal_status IN ('DUE_SOON','EXPIRED') ORDER BY expiry_date")


def assets_with_repeated_maintenance(min_count=2):
    return query_all(
        """SELECT a.asset_code, a.name, COUNT(m.id) AS maintenance_count
           FROM maintenance m JOIN assets a ON m.asset_id = a.id
           GROUP BY a.id HAVING COUNT(m.id) >= %s ORDER BY maintenance_count DESC""",
        (min_count,),
    )


def assets_with_high_maintenance_cost(limit=5):
    return query_all(
        """SELECT a.asset_code, a.name, SUM(m.cost) AS total_cost
           FROM maintenance m JOIN assets a ON m.asset_id = a.id
           GROUP BY a.id ORDER BY total_cost DESC LIMIT %s""",
        (limit,),
    )


def department_highest_asset_value():
    return query_one(
        """SELECT d.name, COALESCE(SUM(a.current_value),0) AS total_value
           FROM assets a JOIN departments d ON a.department_id = d.id
           WHERE a.is_deleted = 0 GROUP BY d.name ORDER BY total_value DESC LIMIT 1""")


def pending_requests_count():
    return query_one("SELECT COUNT(*) c FROM asset_requests WHERE status='PENDING'")["c"]


def unassigned_assets():
    return query_all(
        "SELECT asset_code, name, location FROM assets WHERE status='AVAILABLE' AND is_deleted=0")


def expiring_warranties(days=60):
    return query_all(
        """SELECT asset_code, name, warranty_end FROM assets
           WHERE warranty_end BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
           AND is_deleted = 0 ORDER BY warranty_end""",
        (days,),
    )


def underutilized_assets():
    """Assets available (unused) for a long time - simple heuristic on updated_at."""
    return query_all(
        """SELECT asset_code, name, updated_at FROM assets
           WHERE status='AVAILABLE' AND is_deleted=0
           AND updated_at < DATE_SUB(CURDATE(), INTERVAL 90 DAY)""")


def total_assets_count():
    return query_one("SELECT COUNT(*) c FROM assets WHERE is_deleted=0")["c"]
