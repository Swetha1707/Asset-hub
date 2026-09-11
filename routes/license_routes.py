from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

license_bp = Blueprint("license", __name__)

EXPORT_COLUMNS = [
    ("software_name", "Software"), ("license_type", "Type"), ("vendor", "Vendor"),
    ("expiry_date", "Expiry"), ("seats_total", "Total Seats"), ("seats_used", "Used Seats"),
    ("renewal_status", "Renewal Status"), ("cost", "Cost"),
]


def _fetch(args):
    where = ["1=1"]; params = []
    if args.get("q"):
        where.append("software_name LIKE %s"); params.append(f"%{args['q']}%")
    if args.get("renewal_status"):
        where.append("renewal_status=%s"); params.append(args["renewal_status"])
    if args.get("department_id"):
        where.append("department_id=%s"); params.append(args["department_id"])
    sql = f"SELECT * FROM licenses WHERE {' AND '.join(where)} ORDER BY expiry_date ASC"
    return query_all(sql, params)


@license_bp.route("/licenses")
@login_required
@permission_required("MANAGE_LICENSES")
def licenses_page():
    departments = query_all("SELECT * FROM departments ORDER BY name")
    return render_template("licenses.html", departments=departments)


@license_bp.route("/api/licenses")
@login_required
@permission_required("MANAGE_LICENSES")
def api_list_licenses():
    rows = _fetch(request.args)
    active = len([r for r in rows if r["renewal_status"] == "OK"])
    expiring = len([r for r in rows if r["renewal_status"] == "DUE_SOON"])
    expired = len([r for r in rows if r["renewal_status"] == "EXPIRED"])
    return jsonify({"data": rows, "active": active, "expiring": expiring, "expired": expired})


@license_bp.route("/api/licenses", methods=["POST"])
@login_required
@permission_required("MANAGE_LICENSES")
def api_create_license():
    user = current_user()
    d = request.json
    if not d.get("software_name"):
        return jsonify({"error": "Software name is required"}), 400
    execute(
        """INSERT INTO licenses (software_name,license_key,license_type,vendor,purchase_date,
             start_date,expiry_date,cost,seats_total,seats_used,department_id,renewal_status,
             auto_renewal,notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d["software_name"], d.get("license_key"), d.get("license_type"), d.get("vendor"),
         d.get("purchase_date") or None, d.get("start_date") or None, d.get("expiry_date") or None,
         d.get("cost") or 0, d.get("seats_total") or 1, d.get("seats_used") or 0,
         d.get("department_id") or None, d.get("renewal_status", "OK"),
         1 if d.get("auto_renewal") else 0, d.get("notes")),
    )
    log_activity(user, "LICENSE_ADDED", "LICENSES", f"Added license {d['software_name']}")
    return jsonify({"message": "License added successfully."}), 201


@license_bp.route("/api/licenses/<int:lic_id>", methods=["PUT"])
@login_required
@permission_required("MANAGE_LICENSES")
def api_update_license(lic_id):
    user = current_user()
    lic = query_one("SELECT * FROM licenses WHERE id=%s", (lic_id,))
    if not lic:
        return jsonify({"error": "License not found"}), 404
    d = request.json
    fields = ["software_name", "license_key", "license_type", "vendor", "purchase_date",
              "start_date", "expiry_date", "cost", "seats_total", "seats_used",
              "department_id", "renewal_status", "auto_renewal", "notes"]
    updates, params = [], []
    for f in fields:
        if f in d:
            updates.append(f"{f}=%s"); params.append(d[f] or None)
    if updates:
        params.append(lic_id)
        execute(f"UPDATE licenses SET {', '.join(updates)} WHERE id=%s", params)
    log_activity(user, "LICENSE_UPDATED", "LICENSES", f"Updated license {lic['software_name']}")
    return jsonify({"message": "License updated successfully."})


@license_bp.route("/api/licenses/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_licenses(fmt):
    user = current_user()
    rows = _fetch(request.args)
    if fmt == "csv":
        buf = export_csv(rows, EXPORT_COLUMNS); fname = build_filename("Licenses", "csv"); mt = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, EXPORT_COLUMNS, "Licenses"); fname = build_filename("Licenses", "xlsx")
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, EXPORT_COLUMNS, "License Report"); fname = build_filename("Licenses", "pdf")
        mt = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400
    log_activity(user, "REPORT_EXPORTED", "LICENSES", f"Exported {len(rows)} license(s) as {fmt.upper()}")
    return send_file(buf, mimetype=mt, as_attachment=True, download_name=fname)
