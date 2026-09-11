from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query_all, query_one
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

department_bp = Blueprint("department", __name__)

EXPORT_COLUMNS = [
    ("asset_code", "Asset ID"), ("name", "Asset"), ("assigned_employee_name", "Assigned To"),
    ("status", "Status"), ("current_value", "Value"),
]


@department_bp.route("/departments")
@login_required
@permission_required("VIEW_ASSETS")
def departments_page():
    return render_template("departments.html")


@department_bp.route("/api/departments")
@login_required
@permission_required("VIEW_ASSETS")
def api_list_departments():
    rows = query_all(
        """SELECT d.id, d.name, d.head_name,
                  COUNT(a.id) AS total_assets,
                  COALESCE(SUM(a.current_value),0) AS total_value,
                  SUM(CASE WHEN a.status='ASSIGNED' THEN 1 ELSE 0 END) AS assigned_assets,
                  SUM(CASE WHEN a.status='AVAILABLE' THEN 1 ELSE 0 END) AS available_assets,
                  SUM(CASE WHEN a.status='UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_assets
           FROM departments d
           LEFT JOIN assets a ON a.department_id = d.id AND a.is_deleted = 0
           GROUP BY d.id ORDER BY d.name""")
    return jsonify({"data": rows})


@department_bp.route("/api/departments/<int:dept_id>/assets")
@login_required
@permission_required("VIEW_ASSETS")
def api_department_assets(dept_id):
    dept = query_one("SELECT * FROM departments WHERE id=%s", (dept_id,))
    if not dept:
        return jsonify({"error": "Department not found"}), 404
    rows = query_all(
        """SELECT a.id, a.asset_code, a.name, a.status, a.current_value,
                  e.name AS assigned_employee_name, e.id AS assigned_employee_id
           FROM assets a LEFT JOIN employees e ON a.assigned_employee_id = e.id
           WHERE a.department_id=%s AND a.is_deleted=0 ORDER BY a.name""", (dept_id,))
    return jsonify({"department": dept, "assets": rows})


@department_bp.route("/api/departments/<int:dept_id>/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_department(dept_id, fmt):
    user = current_user()
    dept = query_one("SELECT * FROM departments WHERE id=%s", (dept_id,))
    rows = query_all(
        """SELECT a.asset_code, a.name, a.status, a.current_value,
                  e.name AS assigned_employee_name
           FROM assets a LEFT JOIN employees e ON a.assigned_employee_id = e.id
           WHERE a.department_id=%s AND a.is_deleted=0""", (dept_id,))
    prefix = f"{dept['name']}_Assets" if dept else "Department_Assets"
    if fmt == "csv":
        buf = export_csv(rows, EXPORT_COLUMNS); fname = build_filename(prefix, "csv"); mt = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, EXPORT_COLUMNS, "Dept Assets"); fname = build_filename(prefix, "xlsx")
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, EXPORT_COLUMNS, f"{dept['name']} Asset Report"); fname = build_filename(prefix, "pdf")
        mt = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400
    log_activity(user, "REPORT_EXPORTED", "DEPARTMENTS", f"Exported {dept['name']} assets as {fmt.upper()}")
    return send_file(buf, mimetype=mt, as_attachment=True, download_name=fname)
