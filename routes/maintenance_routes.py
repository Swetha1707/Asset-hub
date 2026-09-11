from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

maintenance_bp = Blueprint("maintenance", __name__)
def _my_employee_id(user):
    row = query_one(
        "SELECT id FROM employees WHERE user_id=%s",
        (user["id"],)
    )

    return row["id"] if row else None
EXPORT_COLUMNS = [
    ("asset_code", "Asset ID"), ("asset_name", "Asset"), ("maintenance_type", "Type"),
    ("problem", "Problem"), ("vendor", "Vendor"), ("start_date", "Start"),
    ("expected_completion", "Expected Completion"), ("status", "Status"), ("cost", "Cost"),
]


def _fetch(args):
    where = ["1=1"]; params = []
    if args.get("status"):
        where.append("m.status=%s"); params.append(args["status"])
    if args.get("q"):
        where.append("(a.asset_code LIKE %s OR a.name LIKE %s)")
        like = f"%{args['q']}%"; params += [like, like]
    sql = f"""SELECT m.*, a.asset_code, a.name AS asset_name FROM maintenance m
              JOIN assets a ON m.asset_id = a.id WHERE {' AND '.join(where)}
              ORDER BY m.start_date DESC"""
    return query_all(sql, params)

@maintenance_bp.route("/my-maintenance")
@login_required
def employee_maintenance_page():
    user = current_user()

    if user["role_name"] != "EMPLOYEE":
        return jsonify({"error": "Employee page only"}), 403

    return render_template(
        "employee_maintenance.html",
        user=user
    )
@maintenance_bp.route("/api/my-maintenance", methods=["POST"])
@login_required
def api_create_employee_maintenance():
    user = current_user()

    if user["role_name"] != "EMPLOYEE":
        return jsonify({"error": "Forbidden"}), 403

    emp_id = _my_employee_id(user)

    d = request.json

    asset_id = d.get("asset_id")
    problem = (d.get("problem") or "").strip()

    if not asset_id or not problem:
        return jsonify({
            "error": "Asset and problem are required"
        }), 400

    asset = query_one(
        """SELECT id FROM assets
           WHERE id=%s
             AND assigned_employee_id=%s""",
        (asset_id, emp_id)
    )

    if not asset:
        return jsonify({
            "error": "This asset is not assigned to you"
        }), 403

    execute(
        """INSERT INTO maintenance_requests
           (employee_id, asset_id, problem, description)
           VALUES (%s,%s,%s,%s)""",
        (
            emp_id,
            asset_id,
            problem,
            d.get("description")
        )
    )

    return jsonify({
        "message": "Maintenance request submitted."
    }), 201
@maintenance_bp.route("/api/my-maintenance")
@login_required
def api_my_maintenance():
    user = current_user()

    emp_id = _my_employee_id(user)

    rows = query_all(
        """SELECT mr.*, a.asset_code, a.name AS asset_name
           FROM maintenance_requests mr
           JOIN assets a ON mr.asset_id=a.id
           WHERE mr.employee_id=%s
           ORDER BY mr.created_at DESC""",
        (emp_id,)
    )

    return jsonify({"data": rows})
@maintenance_bp.route("/maintenance")
@login_required
@permission_required("MANAGE_MAINTENANCE")
def maintenance_page():
    return render_template("maintenance.html")


@maintenance_bp.route("/api/maintenance")
@login_required
@permission_required("MANAGE_MAINTENANCE")
def api_list_maintenance():
    rows = _fetch(request.args)
    upcoming = [r for r in rows if r["status"] == "SCHEDULED"]
    overdue = [r for r in rows if r["status"] == "IN_PROGRESS"]
    total_cost = sum(float(r["cost"] or 0) for r in rows)
    return jsonify({"data": rows, "upcoming_count": len(upcoming), "overdue_count": len(overdue), "total_cost": total_cost})


@maintenance_bp.route("/api/maintenance", methods=["POST"])
@login_required
@permission_required("MANAGE_MAINTENANCE")
def api_create_maintenance():
    user = current_user()
    d = request.json
    if not d.get("asset_id"):
        return jsonify({"error": "Asset is required"}), 400
    execute(
        """INSERT INTO maintenance (asset_id,maintenance_type,problem,description,vendor,technician,
             start_date,expected_completion,cost,status,remarks)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d["asset_id"], d.get("maintenance_type"), d.get("problem"), d.get("description"),
         d.get("vendor"), d.get("technician"), d.get("start_date") or None,
         d.get("expected_completion") or None, d.get("cost") or 0,
         d.get("status", "SCHEDULED"), d.get("remarks")),
    )
    execute("UPDATE assets SET status='UNDER_MAINTENANCE' WHERE id=%s", (d["asset_id"],))
    log_activity(user, "MAINTENANCE_CREATED", "MAINTENANCE", f"Scheduled maintenance for asset #{d['asset_id']}")
    return jsonify({"message": "Maintenance record created successfully."}), 201


@maintenance_bp.route("/api/maintenance/<int:m_id>", methods=["PUT"])
@login_required
@permission_required("MANAGE_MAINTENANCE")
def api_update_maintenance(m_id):
    user = current_user()
    m = query_one("SELECT * FROM maintenance WHERE id=%s", (m_id,))
    if not m:
        return jsonify({"error": "Maintenance record not found"}), 404
    d = request.json
    fields = ["maintenance_type", "problem", "description", "vendor", "technician",
              "start_date", "expected_completion", "actual_completion", "cost", "status", "remarks"]
    updates, params = [], []
    for f in fields:
        if f in d:
            updates.append(f"{f}=%s"); params.append(d[f] or None)
    if updates:
        params.append(m_id)
        execute(f"UPDATE maintenance SET {', '.join(updates)} WHERE id=%s", params)
    if d.get("status") == "COMPLETED":
        execute("UPDATE assets SET status='AVAILABLE' WHERE id=%s", (m["asset_id"],))
    log_activity(user, "MAINTENANCE_UPDATED", "MAINTENANCE", f"Updated maintenance #{m_id}")
    return jsonify({"message": "Maintenance record updated successfully."})


@maintenance_bp.route("/api/maintenance/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_maintenance(fmt):
    user = current_user()
    rows = _fetch(request.args)
    if fmt == "csv":
        buf = export_csv(rows, EXPORT_COLUMNS); fname = build_filename("Maintenance", "csv"); mt = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, EXPORT_COLUMNS, "Maintenance"); fname = build_filename("Maintenance", "xlsx")
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, EXPORT_COLUMNS, "Maintenance Report"); fname = build_filename("Maintenance", "pdf")
        mt = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400
    log_activity(user, "REPORT_EXPORTED", "MAINTENANCE", f"Exported {len(rows)} maintenance record(s) as {fmt.upper()}")
    return send_file(buf, mimetype=mt, as_attachment=True, download_name=fname)
