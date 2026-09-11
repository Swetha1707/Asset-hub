import os
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

asset_bp = Blueprint("asset", __name__)

EXPORT_COLUMNS = [
    ("asset_code", "Asset ID"), ("name", "Asset Name"), ("category_name", "Category"),
    ("brand", "Brand"), ("model", "Model"), ("serial_number", "Serial No."),
    ("department_name", "Department"), ("assigned_employee_name", "Assigned To"),
    ("status", "Status"), ("condition_status", "Condition"), ("current_value", "Value"),
]


def _build_filters(args):
    where = ["a.is_deleted = 0"]
    params = []
    if args.get("q"):
        where.append("""(a.asset_code LIKE %s OR a.name LIKE %s OR a.serial_number LIKE %s
                         OR a.brand LIKE %s OR a.model LIKE %s OR e.name LIKE %s)""")
        like = f"%{args['q']}%"
        params += [like] * 6
    if args.get("category_id"):
        where.append("a.category_id = %s"); params.append(args["category_id"])
    if args.get("department_id"):
        where.append("a.department_id = %s"); params.append(args["department_id"])
    if args.get("status"):
        where.append("a.status = %s"); params.append(args["status"])
    if args.get("condition"):
        where.append("a.condition_status = %s"); params.append(args["condition"])
    if args.get("location"):
        where.append("a.location LIKE %s"); params.append(f"%{args['location']}%")
    if args.get("assigned") == "assigned":
        where.append("a.assigned_employee_id IS NOT NULL")
    elif args.get("assigned") == "unassigned":
        where.append("a.assigned_employee_id IS NULL")
    if args.get("date_from"):
        where.append("a.purchase_date >= %s"); params.append(args["date_from"])
    if args.get("date_to"):
        where.append("a.purchase_date <= %s"); params.append(args["date_to"])
    return " AND ".join(where), params


def _fetch_filtered(args, limit=None, offset=None):
    where_sql, params = _build_filters(args)
    sql = f"""
        SELECT a.*, ac.name AS category_name, d.name AS department_name,
               e.name AS assigned_employee_name
        FROM assets a
        LEFT JOIN asset_categories ac ON a.category_id = ac.id
        LEFT JOIN departments d ON a.department_id = d.id
        LEFT JOIN employees e ON a.assigned_employee_id = e.id
        WHERE {where_sql}
        ORDER BY a.updated_at DESC
    """
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params = params + [limit, offset]
    return query_all(sql, params)


@asset_bp.route("/assets")
@login_required
@permission_required("VIEW_ASSETS")
def assets_page():
    categories = query_all("SELECT * FROM asset_categories ORDER BY name")
    departments = query_all("SELECT * FROM departments ORDER BY name")
    return render_template("assets.html", categories=categories, departments=departments)


@asset_bp.route("/api/assets")
@login_required
@permission_required("VIEW_ASSETS")
def api_list_assets():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 15))
    where_sql, params = _build_filters(request.args)
    total = query_one(
        f"""SELECT COUNT(*) c FROM assets a
            LEFT JOIN employees e ON a.assigned_employee_id = e.id
            WHERE {where_sql}""", params)["c"]
    rows = _fetch_filtered(request.args, limit=per_page, offset=(page - 1) * per_page)
    return jsonify({"data": rows, "total": total, "page": page, "per_page": per_page})


@asset_bp.route("/api/assets/<int:asset_id>")
@login_required
@permission_required("VIEW_ASSETS")
def api_get_asset(asset_id):
    asset = query_one(
        """SELECT a.*, ac.name AS category_name, d.name AS department_name,
                  e.name AS assigned_employee_name
           FROM assets a
           LEFT JOIN asset_categories ac ON a.category_id = ac.id
           LEFT JOIN departments d ON a.department_id = d.id
           LEFT JOIN employees e ON a.assigned_employee_id = e.id
           WHERE a.id = %s AND a.is_deleted = 0""", (asset_id,))
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    maintenance = query_all("SELECT * FROM maintenance WHERE asset_id=%s ORDER BY start_date DESC", (asset_id,))
    assignments = query_all(
        """SELECT aa.*, e.name AS employee_name FROM asset_assignments aa
           JOIN employees e ON aa.employee_id = e.id
           WHERE aa.asset_id=%s ORDER BY aa.assigned_date DESC""", (asset_id,))
    requests_ = query_all(
        """SELECT r.* FROM asset_requests r WHERE r.assigned_asset_id=%s ORDER BY r.created_at DESC""",
        (asset_id,))
    documents = query_all("SELECT * FROM documents WHERE asset_id=%s", (asset_id,))

    return jsonify({
        "asset": asset, "maintenance": maintenance, "assignments": assignments,
        "requests": requests_, "documents": documents,
    })


@asset_bp.route("/api/assets", methods=["POST"])
@login_required
@permission_required("ADD_ASSETS")
def api_create_asset():
    user = current_user()
    d = request.form if request.form else request.json
    required = ["asset_code", "name"]

    for f in required: 
        if not d.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400

    category_id = d.get("category_id")
    new_category_name = (d.get("new_category_name") or "").strip()

    if not category_id:
        if not new_category_name:
            return jsonify({"error": "Category name is required"}), 400

        existing_category = query_one(
            "SELECT id FROM asset_categories WHERE LOWER(name)=LOWER(%s)",
            (new_category_name,)
        )

        if existing_category:
            category_id = existing_category["id"]
        else:
            new_category = execute(
                "INSERT INTO asset_categories (name, group_name) VALUES (%s, %s)",
                (new_category_name, "OTHER")
            )
            category_id = new_category["lastrowid"]

    if query_one("SELECT id FROM assets WHERE asset_code=%s", (d["asset_code"],)):
        return jsonify({"error": "Asset ID already exists"}), 400
    if d.get("serial_number") and query_one("SELECT id FROM assets WHERE serial_number=%s", (d["serial_number"],)):
        return jsonify({"error": "Serial number already exists"}), 400

    image_path = None
    if "image" in request.files and request.files["image"].filename:
        f = request.files["image"]
        filename = secure_filename(f"{d['asset_code']}_{f.filename}")
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        f.save(os.path.join(upload_dir, filename))
        image_path = f"uploads/{filename}"

    result = execute(
        """INSERT INTO assets (asset_code,name,category_id,brand,model,serial_number,purchase_date,
             purchase_cost,current_value,warranty_start,warranty_end,vendor,department_id,location,
             assigned_employee_id,status,condition_status,description,image_path)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d["asset_code"], d["name"], category_id, d.get("brand"), d.get("model"),         d.get("serial_number") or None, d.get("purchase_date") or None, d.get("purchase_cost") or 0,
         d.get("current_value") or 0, d.get("warranty_start") or None, d.get("warranty_end") or None,
         d.get("vendor"), d.get("department_id") or None, d.get("location"),
         d.get("assigned_employee_id") or None, d.get("status", "AVAILABLE"),
         d.get("condition_status", "NEW"), d.get("description"), image_path),
    )
    log_activity(user, "ASSET_ADDED", "ASSETS", f"Added asset {d['asset_code']} - {d['name']}")
    return jsonify({"message": "Asset added successfully.", "id": result["lastrowid"]}), 201


@asset_bp.route("/api/assets/<int:asset_id>", methods=["PUT"])
@login_required
@permission_required("EDIT_ASSETS")
def api_update_asset(asset_id):
    user = current_user()
    asset = query_one("SELECT * FROM assets WHERE id=%s AND is_deleted=0", (asset_id,))
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    d = request.form if request.form else request.json
    fields = ["name", "category_id", "brand", "model", "serial_number", "purchase_date",
              "purchase_cost", "current_value", "warranty_start", "warranty_end", "vendor",
              "department_id", "location", "assigned_employee_id", "status", "condition_status",
              "description"]
    updates, params = [], []
    for f in fields:
        if f in d:
            updates.append(f"{f}=%s")
            params.append(d[f] or None)
    if not updates:
        return jsonify({"error": "No fields to update"}), 400
    params.append(asset_id)
    execute(f"UPDATE assets SET {', '.join(updates)} WHERE id=%s", params)
    log_activity(user, "ASSET_EDITED", "ASSETS", f"Edited asset {asset['asset_code']}")
    return jsonify({"message": "Asset updated successfully."})


@asset_bp.route("/api/assets/<int:asset_id>", methods=["DELETE"])
@login_required
@permission_required("DELETE_ASSETS")
def api_delete_asset(asset_id):
    user = current_user()
    asset = query_one("SELECT * FROM assets WHERE id=%s AND is_deleted=0", (asset_id,))
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
    execute("UPDATE assets SET is_deleted=1 WHERE id=%s", (asset_id,))
    log_activity(user, "ASSET_DELETED", "ASSETS", f"Soft-deleted asset {asset['asset_code']}")
    return jsonify({"message": "Asset deleted successfully."})


@asset_bp.route("/api/assets/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_assets(fmt):
    user = current_user()
    rows = _fetch_filtered(request.args)
    tags = [request.args.get(k) for k in ("department_id", "status", "category_id") if request.args.get(k)]
    prefix = "Assets_Export" if not tags else "Filtered_Assets"

    if fmt == "csv":
        buf = export_csv(rows, EXPORT_COLUMNS)
        fname = build_filename(prefix, "csv")
        mimetype = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, EXPORT_COLUMNS, "Assets")
        fname = build_filename(prefix, "xlsx")
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, EXPORT_COLUMNS, "Asset Report")
        fname = build_filename(prefix, "pdf")
        mimetype = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400

    log_activity(user, "REPORT_EXPORTED", "ASSETS", f"Exported {len(rows)} asset(s) as {fmt.upper()} ({fname})")
    return send_file(buf, mimetype=mimetype, as_attachment=True, download_name=fname)
