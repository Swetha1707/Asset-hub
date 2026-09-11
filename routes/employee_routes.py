from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity
from utils.exporter import export_csv, export_xlsx, export_pdf, build_filename

employee_bp = Blueprint("employee", __name__)

EXPORT_COLUMNS = [
    ("employee_code", "Employee ID"), ("name", "Name"), ("email", "Email"),
    ("department_name", "Department"), ("designation", "Designation"),
    ("status", "Status"), ("asset_count", "Assets Held"),
]


@employee_bp.route("/employees")
@login_required
@permission_required("VIEW_EMPLOYEES")
def employees_page():
    departments = query_all("SELECT * FROM departments ORDER BY name")
    return render_template("employees.html", departments=departments)


def _fetch_employees(args):
    where = ["1=1"]
    params = []
    if args.get("q"):
        where.append("(e.name LIKE %s OR e.employee_code LIKE %s OR e.email LIKE %s)")
        like = f"%{args['q']}%"
        params += [like, like, like]
    if args.get("department_id"):
        where.append("e.department_id = %s"); params.append(args["department_id"])
    if args.get("status"):
        where.append("e.status = %s"); params.append(args["status"])
    sql = f"""
        SELECT e.*, d.name AS department_name,
               (SELECT COUNT(*) FROM assets a WHERE a.assigned_employee_id = e.id AND a.is_deleted=0) AS asset_count
        FROM employees e LEFT JOIN departments d ON e.department_id = d.id
        WHERE {' AND '.join(where)} ORDER BY e.name
    """
    return query_all(sql, params)


@employee_bp.route("/api/employees")
@login_required
@permission_required("VIEW_EMPLOYEES")
def api_list_employees():
    return jsonify({"data": _fetch_employees(request.args)})


@employee_bp.route("/api/employees/<int:emp_id>")
@login_required
@permission_required("VIEW_EMPLOYEES")
def api_get_employee(emp_id):
    emp = query_one(
        """SELECT e.*, d.name AS department_name FROM employees e
           LEFT JOIN departments d ON e.department_id = d.id WHERE e.id=%s""", (emp_id,))
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    current_assets = query_all(
        "SELECT * FROM assets WHERE assigned_employee_id=%s AND is_deleted=0", (emp_id,))
    history = query_all(
        """SELECT aa.*, a.asset_code, a.name AS asset_name FROM asset_assignments aa
           JOIN assets a ON aa.asset_id = a.id WHERE aa.employee_id=%s ORDER BY aa.assigned_date DESC""",
        (emp_id,))
    pending_requests = query_all(
        "SELECT * FROM asset_requests WHERE employee_id=%s ORDER BY created_at DESC", (emp_id,))
    return jsonify({
        "employee": emp, "current_assets": current_assets,
        "history": history, "requests": pending_requests,
    })


@employee_bp.route("/api/employees", methods=["POST"])
@login_required
@permission_required("MANAGE_EMPLOYEES")
def api_create_employee():
    user = current_user()
    d = request.json
    for f in ["employee_code", "name", "email"]:
        if not d.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400
    if query_one("SELECT id FROM employees WHERE employee_code=%s", (d["employee_code"],)):
        return jsonify({"error": "Employee ID already exists"}), 400
    result = execute(
        """INSERT INTO employees (employee_code,name,email,phone,department_id,designation,joining_date,status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d["employee_code"], d["name"], d["email"], d.get("phone"), d.get("department_id") or None,
         d.get("designation"), d.get("joining_date") or None, d.get("status", "ACTIVE")),
    )
    log_activity(user, "EMPLOYEE_ADDED", "EMPLOYEES", f"Added employee {d['employee_code']}")
    return jsonify({"message": "Employee added successfully.", "id": result["lastrowid"]}), 201


@employee_bp.route("/api/employees/<int:emp_id>", methods=["PUT"])
@login_required
@permission_required("MANAGE_EMPLOYEES")
def api_update_employee(emp_id):
    user = current_user()
    emp = query_one("SELECT * FROM employees WHERE id=%s", (emp_id,))
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    d = request.json
    fields = ["name", "email", "phone", "department_id", "designation", "joining_date", "status"]
    updates, params = [], []
    for f in fields:
        if f in d:
            updates.append(f"{f}=%s"); params.append(d[f] or None)
    if updates:
        params.append(emp_id)
        execute(f"UPDATE employees SET {', '.join(updates)} WHERE id=%s", params)
    log_activity(user, "EMPLOYEE_EDITED", "EMPLOYEES", f"Edited employee {emp['employee_code']}")
    return jsonify({"message": "Employee updated successfully."})


@employee_bp.route("/api/employees/export/<fmt>")
@login_required
@permission_required("EXPORT_REPORTS")
def api_export_employees(fmt):
    user = current_user()
    rows = _fetch_employees(request.args)
    if fmt == "csv":
        buf = export_csv(rows, EXPORT_COLUMNS); fname = build_filename("Employees", "csv"); mt = "text/csv"
    elif fmt == "xlsx":
        buf = export_xlsx(rows, EXPORT_COLUMNS, "Employees"); fname = build_filename("Employees", "xlsx")
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        buf = export_pdf(rows, EXPORT_COLUMNS, "Employee Report"); fname = build_filename("Employees", "pdf")
        mt = "application/pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400
    log_activity(user, "REPORT_EXPORTED", "EMPLOYEES", f"Exported {len(rows)} employee(s) as {fmt.upper()}")
    return send_file(buf, mimetype=mt, as_attachment=True, download_name=fname)
