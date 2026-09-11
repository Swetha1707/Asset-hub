from database.db import query_all, query_one


def _employee_id(user):
    row = query_one(
        "SELECT id FROM employees WHERE user_id=%s",
        (user["id"],)
    )
    return row["id"] if row else None


def employee_answer(question, user):
    q = question.strip().lower()

    emp_id = _employee_id(user)

    if not emp_id:
        return {
            "text": "Your employee profile is not linked to this account.",
            "data": None
        }

    # -------------------------------------------------
    # 1. ASSET REQUEST GUIDANCE
    # -------------------------------------------------

    if (
        "how to request" in q
        or "create request" in q
        or "new request" in q
        or "asset request" in q and "how" in q
    ):
        return {
            "text":
                "To request an asset: open My Asset Request, "
                "click '+ New Asset Request', select the required "
                "asset category, enter the reason and required date, "
                "then submit the request. You can check its status "
                "later from My Asset Request or My Requests.",
            "data": None
        }

    # -------------------------------------------------
    # 2. OWN REQUEST STATUS ONLY
    # -------------------------------------------------

    if (
        "my request" in q
        or "request status" in q
        or "status of request" in q
    ):
        rows = query_all(
            """
            SELECT r.id,
                   r.status,
                   r.reason,
                   r.admin_comment,
                   r.created_at,
                   c.name AS category_name,
                   a.asset_code AS assigned_asset_code
            FROM asset_requests r
            LEFT JOIN asset_categories c
                   ON r.category_id = c.id
            LEFT JOIN assets a
                   ON r.assigned_asset_id = a.id
            WHERE r.employee_id=%s
            ORDER BY r.created_at DESC
            LIMIT 10
            """,
            (emp_id,)
        )

        if not rows:
            return {
                "text": "You currently have no asset requests.",
                "data": []
            }

        latest = rows[0]

        status = latest["status"]

        if status == "PENDING":
            explanation = (
                "Your request is pending. "
                "It has been submitted and is waiting for admin review."
            )

        elif status == "APPROVED":
            explanation = (
                "Your request has been approved."
            )

        elif status == "REJECTED":
            explanation = (
                "Your request was rejected."
            )

        elif status == "ISSUED":
            explanation = (
                "Your request was approved and the asset has been issued."
            )

        else:
            explanation = f"Your request status is {status}."

        if latest.get("admin_comment"):
            explanation += (
                f" Admin response: {latest['admin_comment']}"
            )

        return {
            "text": explanation,
            "data": rows
        }

    # -------------------------------------------------
    # 3. RETURN REQUEST GUIDANCE
    # -------------------------------------------------

    if "return" in q and (
        "request" in q
        or "asset" in q
        or "how" in q
    ):
        return {
            "text":
                "To return an assigned asset, open Return Request, "
                "click '+ New Return Request', select your assigned asset, "
                "enter the reason for return and submit it. "
                "You can check the response and status on the same page.",
            "data": None
        }

    # -------------------------------------------------
    # 4. MAINTENANCE REQUEST GUIDANCE
    # -------------------------------------------------

    if (
        "maintenance request" in q
        or "report problem" in q
        or "complaint" in q
    ):
        return {
            "text":
                "To report an asset problem, open Maintenance Request, "
                "click 'Report Problem', select your assigned asset, "
                "enter a short problem title and describe what happened. "
                "Include symptoms, when the problem started, and any "
                "error message you see.",
            "data": None
        }

    # -------------------------------------------------
    # 5. COMPLAINT DESCRIPTION HELP
    # -------------------------------------------------

    if (
        "write complaint" in q
        or "complaint description" in q
        or "help me describe" in q
    ):
        return {
            "text":
                "A good maintenance complaint should contain: "
                "1) the problem, 2) when it started, "
                "3) what happens when you use the asset, "
                "4) any error message, and 5) whether the issue "
                "prevents you from working. Example: "
                "'The laptop screen started flickering this morning. "
                "The display becomes blank after a few minutes and "
                "restarting does not solve the issue.'",
            "data": None
        }

    # -------------------------------------------------
    # 6. BASIC TROUBLESHOOTING
    # -------------------------------------------------

    if any(word in q for word in [
        "not working",
        "problem",
        "troubleshoot",
        "screen",
        "keyboard",
        "mouse",
        "printer",
        "wifi",
        "laptop"
    ]):
        return {
            "text":
                "You can try basic safe checks first: restart the device, "
                "check power and cable connections, reconnect accessories, "
                "and note any error message. Do not open or repair company "
                "equipment yourself. If the issue continues, submit a "
                "Maintenance Request with the symptoms.",
            "data": None
        }

    # -------------------------------------------------
    # 7. COMPANY POLICY / RULES
    # -------------------------------------------------

    if (
        "policy" in q
        or "rule" in q
        or "company rules" in q
    ):
        return {
            "text":
                "I can explain company asset policies that are provided "
                "to this assistant. I cannot invent company rules. "
                "Please ask about a specific policy, such as asset return, "
                "maintenance reporting, or acceptable asset usage.",
            "data": None
        }

    # -------------------------------------------------
    # BLOCK EVERYTHING ELSE
    # -------------------------------------------------

    return {
        "text":
            "Employee AI can only help with your own requests, "
            "request-status explanations, return requests, maintenance "
            "troubleshooting, complaint descriptions, and company policies. "
            "It cannot access other employees' information or general "
            "company database records.",
        "data": None
    }