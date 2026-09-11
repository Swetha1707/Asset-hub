from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query_all
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

report_bp = Blueprint("report", __name__)

REPORTS = {
    "complete_assets": {
        "label": "Complete Asset Report",
        "sql": """SELECT a.asset_code, a.name, ac.name AS category, d.name AS department,
                          e.name AS assigned_to, a.status, a.current_value
                   FROM assets a
                   LEFT JOIN asset_categories ac ON a.category_id = ac.id
                   LEFT JOIN departments d ON a.department_id = d.id
                   LEFT JOIN employees e ON a.assigned_employee_id = e.id
                   WHERE a.is_deleted = 0""",
        "columns": [("asset_code", "Asset ID"), ("name", "Name"), ("category", "Category"),
                    ("department", "Department"), ("assigned_to", "Assigned To"),
                    ("status", "Status"), ("current_value", "Value")],
    },
    "department_assets": {
        "label": "Department Asset Report",
        "sql": """SELECT d.name AS department, COUNT(a.id) AS total_assets,
                          COALESCE(SUM(a.current_value),0) AS total_value
                   FROM departments d LEFT JOIN assets a ON a.department_id=d.id AND a.is_deleted=0
                   GROUP BY d.name""",
        "columns": [("department", "Department"), ("total_assets", "Total Assets"), ("total_value", "Total Value")],
    },
    "employee_assets": {
        "label": "Employee Asset Report",
        "sql": """SELECT e.employee_code, e.name, COUNT(a.id) AS assets_held
                   FROM employees e LEFT JOIN assets a ON a.assigned_employee_id=e.id AND a.is_deleted=0
                   GROUP BY e.id""",
        "columns": [("employee_code", "Employee ID"), ("name", "Name"), ("assets_held", "Assets Held")],
    },
    "assigned_assets": {
        "label": "Assigned Asset Report",
        "sql": """SELECT a.asset_code, a.name, e.name AS assigned_to, d.name AS department
                   FROM assets a JOIN employees e ON a.assigned_employee_id=e.id
                   LEFT JOIN departments d ON a.department_id=d.id
                   WHERE a.status='ASSIGNED' AND a.is_deleted=0""",
        "columns": [("asset_code", "Asset ID"), ("name", "Name"), ("assigned_to", "Assigned To"), ("department", "Department")],
    },
    "available_assets": {
        "label": "Available Asset Report",
        "sql": """SELECT asset_code, name, location FROM assets WHERE status='AVAILABLE' AND is_deleted=0""",
        "columns": [("asset_code", "Asset ID"), ("name", "Name"), ("location", "Location")],
    },
    "maintenance": {
        "label": "Maintenance Report",
        "sql": """SELECT a.asset_code, m.maintenance_type, m.status, m.cost, m.start_date
                   FROM maintenance m JOIN assets a ON m.asset_id=a.id""",
        "columns": [("asset_code", "Asset ID"), ("maintenance_type", "Type"), ("status", "Status"),
                    ("cost", "Cost"), ("start_date", "Start Date")],
    },
    "licenses": {
        "label": "License Report",
        "sql": "SELECT software_name, vendor, expiry_date, renewal_status, cost FROM licenses",
        "columns": [("software_name", "Software"), ("vendor", "Vendor"), ("expiry_date", "Expiry"),
                    ("renewal_status", "Renewal Status"), ("cost", "Cost")],
    },
    "asset_value": {
        "label": "Asset Value Report",
        "sql": """SELECT ac.name AS category, COUNT(a.id) AS count, COALESCE(SUM(a.current_value),0) AS total_value
                   FROM assets a LEFT JOIN asset_categories ac ON a.category_id=ac.id
                   WHERE a.is_deleted=0 GROUP BY ac.name""",
        "columns": [("category", "Category"), ("count", "Count"), ("total_value", "Total Value")],
    },
    "warranty_expiry": {
        "label": "Warranty Expiry Report",
        "sql": """SELECT asset_code, name, warranty_end FROM assets
                   WHERE warranty_end IS NOT NULL AND is_deleted=0 ORDER BY warranty_end ASC""",
        "columns": [("asset_code", "Asset ID"), ("name", "Name"), ("warranty_end", "Warranty End")],
    },
    "requests": {
        "label": "Asset Request Report",
        "sql": """SELECT e.name AS employee, c.name AS category, r.status, r.created_at
                   FROM asset_requests r JOIN employees e ON r.employee_id=e.id
                   LEFT JOIN asset_categories c ON r.category_id=c.id""",
        "columns": [("employee", "Employee"), ("category", "Category"), ("status", "Status"), ("created_at", "Requested On")],
    },
    "returns": {
        "label": "Asset Return Report",
        "sql": """SELECT a.asset_code, ar.return_date, ar.condition_after, ar.remarks
                   FROM asset_returns ar JOIN assets a ON ar.asset_id = a.id ORDER BY ar.return_date DESC""",
        "columns": [("asset_code", "Asset ID"), ("return_date", "Return Date"), ("condition_after", "Condition"), ("remarks", "Remarks")],
    },
    "audit_activity": {
        "label": "Audit Activity Report",
        "sql": "SELECT username, action, module, description, created_at FROM activity_logs ORDER BY created_at DESC LIMIT 500",
        "columns": [("username", "User"), ("action", "Action"), ("module", "Module"),
                    ("description", "Description"), ("created_at", "Timestamp")],
    },
}


@report_bp.route("/reports")
@login_required
@permission_required("VIEW_REPORTS")
def reports_page():
    return render_template("reports.html", reports=[{"key": k, "label": v["label"]} for k, v in REPORTS.items()])


@report_bp.route("/api/reports/<key>")
@login_required
@permission_required("VIEW_REPORTS")
def api_get_report(key):
    if key not in REPORTS:
        return jsonify({"error": "Unknown report"}), 404
    rows = query_all(REPORTS[key]["sql"])
    return jsonify({"label": REPORTS[key]["label"], "columns": REPORTS[key]["columns"], "data": rows})


@report_bp.route("/api/reports/<key>/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_report(key, fmt):
    if key not in REPORTS:
        return jsonify({"error": "Unknown report"}), 404
    user = current_user()
    report = REPORTS[key]
    rows = query_all(report["sql"])
    columns = report["columns"]
    prefix = report["label"].replace(" ", "_")

    if fmt == "csv":
        buf = export_csv(rows, columns); fname = build_filename(prefix, "csv"); mt = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, columns, report["label"][:31]); fname = build_filename(prefix, "xlsx")
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, columns, report["label"]); fname = build_filename(prefix, "pdf")
        mt = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400

    log_activity(user, "REPORT_EXPORTED", "REPORTS", f"Exported '{report['label']}' as {fmt.upper()}")
    return send_file(buf, mimetype=mt, as_attachment=True, download_name=fname)
