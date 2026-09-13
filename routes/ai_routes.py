"""
AI Assistant routes — ADMIN-ONLY per the mandatory access rule.
permission_required("USE_AI_ASSISTANT") is hard-blocked server-side for
EMPLOYEE role in utils.security.get_user_permissions, so even a manually
crafted request from an Employee account receives HTTP 403.
"""
from ai.openai_ai import ask_openai
from flask import Blueprint, render_template, request, jsonify
from ai.ai_assistant import answer
from ai.employee_ai import employee_answer
from ai import ai_services as svc
from utils.security import login_required, permission_required, current_user, get_user_permissions, log_activity

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/ai-assistant")
@login_required
def ai_assistant_page():
    user = current_user()

    return render_template(
        "ai_assistant.html",
        user=user
    )


@ai_bp.route("/api/ai/ask", methods=["POST"])
@login_required
def api_ai_ask():
    user = current_user()

    question = (
        (request.json or {}).get("question", "").strip()
    )

    if not question:
        return jsonify({
            "error": "Please enter a question."
        }), 400

    if user["role_name"] == "EMPLOYEE":

        employee_prompt = """
You are the AssetHub Employee Assistant.

Help only with:
- asset requests
- return requests
- maintenance requests
- maintenance troubleshooting
- complaint writing
- company asset policies
- the employee's own request status

Never provide other employees' data, admin data,
company-wide database data, financial data, SQL,
or admin actions.

Keep answers short, clear and practical.
"""

        ai_text = ask_openai(
            question,
            employee_prompt
        )

        result = {
            "answer": ai_text
        }

    else:

        perms = get_user_permissions(user)

        

        admin_prompt = """
You are the AssetHub Admin Assistant.

Help with assets, departments, requests, maintenance,
licenses, reports and AssetHub procedures.

Keep answers short and practical.
Never invent database values.
Do not generate destructive SQL.
"""

        ai_text = ask_openai(
            question,
            admin_prompt
        )

        result = {
            "answer": ai_text
        }

    log_activity(
        user,
        "AI_QUERY",
        "AI_ASSISTANT",
        f"Asked: {question[:200]}"
    )

    return jsonify(result)


@ai_bp.route("/api/ai/insights")
@login_required
def api_ai_insights():
    user = current_user()

    if user["role_name"] == "EMPLOYEE":
        return jsonify({
            "insights": [],
            "note": "AI Insights are available only for Admin users."
        })

    perms = get_user_permissions(user)

    if "USE_AI_ASSISTANT" not in perms:
        return jsonify({"error": "Forbidden"}), 403

    insights = []

    expiring = svc.licenses_expiring(30)
    if expiring:
        insights.append({
            "type": "warning",
            "text": f"{len(expiring)} license(s) expire within 30 days.",
            "items": [e["software_name"] for e in expiring]
        })

    repeated = svc.assets_with_repeated_maintenance()
    if repeated:
        insights.append({
            "type": "maintenance",
            "text": f"{len(repeated)} asset(s) have repeated maintenance issues.",
            "items": [r["asset_code"] for r in repeated]
        })

    high_cost = svc.assets_with_high_maintenance_cost(3)
    if high_cost:
        insights.append({
            "type": "cost",
            "text": "Highest maintenance-cost assets identified.",
            "items": [
                f"{r['asset_code']} (₹{float(r['total_cost']):,.0f})"
                for r in high_cost
            ]
        })

    top_dept = svc.department_highest_asset_value()
    if top_dept and top_dept["total_value"]:
        insights.append({
            "type": "value",
            "text": f"{top_dept['name']} has the highest total asset value.",
            "items": [
                f"₹{float(top_dept['total_value']):,.0f}"
            ]
        })

    unassigned = svc.unassigned_assets()
    if unassigned:
        insights.append({
            "type": "unassigned",
            "text": f"{len(unassigned)} asset(s) are currently unassigned.",
            "items": [
                a["asset_code"] for a in unassigned[:10]
            ]
        })

    expiring_warranty = svc.expiring_warranties(60)
    if expiring_warranty:
        insights.append({
            "type": "warranty",
            "text": f"{len(expiring_warranty)} asset(s) have warranties expiring within 60 days.",
            "items": [
                a["asset_code"] for a in expiring_warranty
            ]
        })

    return jsonify({
        "insights": insights,
        "note": "Predictions and insights are generated from current data trends and are not guaranteed outcomes."
    })