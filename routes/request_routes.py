from flask import Blueprint, render_template, request, jsonify
from database.db import query_all, query_one, execute
from utils.security import login_required, permission_required, current_user, log_activity

request_bp = Blueprint("request", __name__)


def _my_employee_id(user):
    row = query_one("SELECT id FROM employees WHERE user_id=%s", (user["id"],))
    return row["id"] if row else None
@request_bp.route("/return-requests")
@login_required
def return_requests_page():
    user = current_user()

    if user["role_name"] != "EMPLOYEE":
        return jsonify({"error": "Employee page only"}), 403

    return render_template("return_requests.html", user=user)
@request_bp.route("/api/my-assigned-assets")
@login_required
def api_my_assigned_assets():
    user = current_user()

    emp_id = _my_employee_id(user)

    if not emp_id:
        return jsonify({"data": []})

    rows = query_all(
        """SELECT id, asset_code, name
           FROM assets
           WHERE assigned_employee_id=%s
             AND status='ASSIGNED'
             AND is_deleted=0
           ORDER BY name""",
        (emp_id,)
    )

    return jsonify({"data": rows})
@request_bp.route("/api/return-requests", methods=["POST"])
@login_required
def api_create_return_request():
    user = current_user()

    if user["role_name"] != "EMPLOYEE":
        return jsonify({"error": "Forbidden"}), 403

    emp_id = _my_employee_id(user)

    d = request.json

    asset_id = d.get("asset_id")

    if not asset_id:
        return jsonify({"error": "Please select an asset"}), 400

    asset = query_one(
        """SELECT id FROM assets
           WHERE id=%s
             AND assigned_employee_id=%s
             AND status='ASSIGNED'""",
        (asset_id, emp_id)
    )

    if not asset:
        return jsonify({"error": "This asset is not assigned to you"}), 403

    existing = query_one(
        """SELECT id FROM return_requests
           WHERE employee_id=%s
             AND asset_id=%s
             AND status='PENDING'""",
        (emp_id, asset_id)
    )

    if existing:
        return jsonify({"error": "Return request already pending"}), 400

    execute(
        """INSERT INTO return_requests
           (employee_id, asset_id, reason, status)
           VALUES (%s,%s,%s,'PENDING')""",
        (
            emp_id,
            asset_id,
            d.get("reason")
        )
    )

    return jsonify({
        "message": "Return request submitted successfully."
    }), 201
@request_bp.route("/api/return-requests")
@login_required
def api_return_requests():
    user = current_user()

    emp_id = _my_employee_id(user)

    if user["role_name"] == "EMPLOYEE":
        rows = query_all(
            """SELECT rr.*, a.asset_code, a.name AS asset_name
               FROM return_requests rr
               JOIN assets a ON rr.asset_id=a.id
               WHERE rr.employee_id=%s
               ORDER BY rr.created_at DESC""",
            (emp_id,)
        )
    else:
        rows = query_all(
            """SELECT rr.*, a.asset_code, a.name AS asset_name,
                      e.name AS employee_name
               FROM return_requests rr
               JOIN assets a ON rr.asset_id=a.id
               JOIN employees e ON rr.employee_id=e.id
               ORDER BY rr.created_at DESC"""
        )

    return jsonify({"data": rows})
@request_bp.route("/my-requests")
@login_required
def my_requests_page():
    user = current_user()

    if user["role_name"] != "EMPLOYEE":
        return jsonify({"error": "Employee page only"}), 403

    return render_template("my_requests.html", user=user)
@request_bp.route("/requests")
@login_required
@permission_required("MANAGE_REQUESTS")
def requests_page():
    user = current_user()
    categories = query_all("SELECT * FROM asset_categories ORDER BY name")
    return render_template("requests.html", user=user, categories=categories)


@request_bp.route("/api/requests")
@login_required
@permission_required("MANAGE_REQUESTS")
def api_list_requests():
    user = current_user()
    where = ["1=1"]
    params = []
    # Employees only ever see their own requests (never anyone else's)
    if user["role_name"] == "EMPLOYEE":
        emp_id = _my_employee_id(user)
        where.append("r.employee_id=%s"); params.append(emp_id)
    if request.args.get("status"):
        where.append("r.status=%s"); params.append(request.args["status"])
    rows = query_all(
        f"""SELECT r.*, e.name AS employee_name, e.employee_code, c.name AS category_name,
                   a.asset_code AS assigned_asset_code
            FROM asset_requests r
            JOIN employees e ON r.employee_id = e.id
            LEFT JOIN asset_categories c ON r.category_id = c.id
            LEFT JOIN assets a ON r.assigned_asset_id = a.id
            WHERE {' AND '.join(where)} ORDER BY r.created_at DESC""", params)
    return jsonify({"data": rows})


@request_bp.route("/api/requests", methods=["POST"])
@login_required
@permission_required("MANAGE_REQUESTS")
def api_create_request():
    user = current_user()
    emp_id = _my_employee_id(user)
    if not emp_id:
        return jsonify({"error": "No employee profile linked to this account."}), 400
    d = request.json
    if not d.get("category_id"):
        return jsonify({"error": "Please select an asset category."}), 400
    execute(
        """INSERT INTO asset_requests (employee_id, category_id, reason, required_date, status)
           VALUES (%s,%s,%s,%s,'PENDING')""",
        (emp_id, d["category_id"], d.get("reason"), d.get("required_date") or None),
    )
    log_activity(user, "REQUEST_CREATED", "REQUESTS", "Submitted a new asset request")
    return jsonify({"message": "Request submitted successfully."}), 201


@request_bp.route("/api/requests/<int:req_id>/decision", methods=["POST"])
@login_required
@permission_required("MANAGE_REQUESTS")
def api_decide_request(req_id):
    user = current_user()
    if user["role_name"] == "EMPLOYEE":
        return jsonify({"error": "Forbidden"}), 403
    d = request.json
    decision = d.get("decision")  # APPROVED / REJECTED
    if decision not in ("APPROVED", "REJECTED"):
        return jsonify({"error": "Invalid decision"}), 400

    req_row = query_one("SELECT * FROM asset_requests WHERE id=%s", (req_id,))
    if not req_row:
        return jsonify({"error": "Request not found"}), 404

    assigned_asset_id = d.get("assigned_asset_id") if decision == "APPROVED" else None
    execute(
        """UPDATE asset_requests SET status=%s, assigned_asset_id=%s, admin_comment=%s, handled_by=%s
           WHERE id=%s""",
        (decision, assigned_asset_id, d.get("comment"), user["id"], req_id),
    )

    if decision == "APPROVED" and assigned_asset_id:
        execute("UPDATE assets SET status='ASSIGNED', assigned_employee_id=%s WHERE id=%s",
                (req_row["employee_id"], assigned_asset_id))
        execute(
            """INSERT INTO asset_assignments (asset_id, employee_id, department_id, assigned_date, notes, created_by)
               VALUES (%s,%s,(SELECT department_id FROM employees WHERE id=%s),CURDATE(),%s,%s)""",
            (assigned_asset_id, req_row["employee_id"], req_row["employee_id"], "Issued via request approval", user["id"]),
        )
        execute("UPDATE asset_requests SET status='ISSUED' WHERE id=%s", (req_id,))
        if decision == "APPROVED" and assigned_asset_id:
            execute("UPDATE asset_requests SET status='ISSUED' WHERE id=%s", (req_id,))

    employee_user = query_one(
        "SELECT user_id FROM employees WHERE id=%s",
        (req_row["employee_id"],)
    )

    if employee_user and employee_user["user_id"]:
        if decision == "APPROVED":
            if assigned_asset_id:
                asset = query_one(
                    "SELECT asset_code, name FROM assets WHERE id=%s",
                    (assigned_asset_id,)
                )
                message = (
                    f"Your request #{req_id} was approved. "
                    f"Asset {asset['asset_code']} - {asset['name']} has been issued to you."
                )
            else:
                message = f"Your request #{req_id} was approved."
        else:
            message = f"Your request #{req_id} was rejected."
            if d.get("comment"):
                message += f" Reason: {d.get('comment')}"

        execute(
            """INSERT INTO notifications
            (user_id, title, message, type, is_read)
            VALUES (%s,%s,%s,%s,0)""",
            (
                employee_user["user_id"],
                "Request Status Updated",
                message,
                "REQUEST"
            )
        )

    log_activity(user, f"REQUEST_{decision}", "REQUESTS",
            f"Request #{req_id} {decision.lower()}")

    return jsonify({"message": f"Request {decision.lower()} successfully."})
    log_activity(user, f"REQUEST_{decision}", "REQUESTS", f"Request #{req_id} {decision.lower()}")
    return jsonify({"message": f"Request {decision.lower()} successfully."})


@request_bp.route("/api/requests/available-assets/<int:category_id>")
@login_required
@permission_required("MANAGE_REQUESTS")
def api_available_assets_for_category(category_id):
    rows = query_all(
        "SELECT id, asset_code, name FROM assets WHERE category_id=%s AND status='AVAILABLE' AND is_deleted=0",
        (category_id,))
    return jsonify({"data": rows})


# ---------------- Asset Return ----------------
@request_bp.route("/api/assets/<int:asset_id>/return", methods=["POST"])
@login_required
@permission_required("EDIT_ASSETS")
def api_return_asset(asset_id):
    user = current_user()
    d = request.json
    assignment = query_one(
        "SELECT * FROM asset_assignments WHERE asset_id=%s AND is_active=1 ORDER BY assigned_date DESC LIMIT 1",
        (asset_id,))
    if not assignment:
        return jsonify({"error": "No active assignment found for this asset."}), 400

    execute(
        """INSERT INTO asset_returns (assignment_id, asset_id, return_date, condition_after,
             damage_notes, accessories_returned, verified_by, remarks)
           VALUES (%s,%s,CURDATE(),%s,%s,%s,%s,%s)""",
        (assignment["id"], asset_id, d.get("condition_after"), d.get("damage_notes"),
         d.get("accessories_returned"), user["id"], d.get("remarks")),
    )
    execute("UPDATE asset_assignments SET is_active=0 WHERE id=%s", (assignment["id"],))
    new_status = "UNDER_MAINTENANCE" if d.get("needs_maintenance") else "AVAILABLE"
    execute("UPDATE assets SET status=%s, assigned_employee_id=NULL, condition_status=%s WHERE id=%s",
            (new_status, d.get("condition_after", "GOOD"), asset_id))
    log_activity(user, "ASSET_RETURNED", "ASSETS", f"Asset #{asset_id} returned, new status {new_status}")
    return jsonify({"message": "Asset return processed successfully."})
