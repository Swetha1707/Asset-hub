"""
Ask Asset AI — the assistant's brain.

Design goals (per spec section 22-25):
  1. Understand natural-language questions about the asset DB.
  2. Never bypass Flask authorization — every call receives the caller's
     permission set and refuses anything the caller isn't allowed to see.
  3. Never run arbitrary user-supplied SQL — only the fixed, parameterized
     functions in ai_services.py are ever invoked.
  4. Modular: swap `answer()` internals for a hosted LLM provider later
     without touching routes/templates (see AI_PROVIDER in config).

This implementation uses transparent keyword/regex intent-matching so it
works fully offline with zero external dependency or API key, while
still being genuinely useful over real, live MySQL data.
"""
import re
from ai import ai_services as svc

# Permission required to use the assistant AT ALL (checked in ai_routes.py)
REQUIRED_PERMISSION = "USE_AI_ASSISTANT"

# Some intents surface admin-only information (e.g. audit-style cost data).
# Map intent -> extra permission required beyond USE_AI_ASSISTANT.
INTENT_PERMISSIONS = {
    "activity_logs": "VIEW_ACTIVITY_LOGS",
}


def _money(v):
    try:
        return f"₹{float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def answer(question, permissions):
    """Return {'text': str, 'data': list|None} for a natural-language question.
    `permissions` is the caller's actual permission set (already resolved
    server-side by utils.security.get_user_permissions)."""
    q = question.strip().lower()

    if REQUIRED_PERMISSION not in permissions:
        return {"text": "You don't have permission to use the AI Assistant.", "data": None}

    # ---- available/status count of a category ----
    m = re.search(r"how many ([a-z ]+?) (?:are |is )?(available|assigned|under maintenance|damaged|retired)", q)
    if m:
        category, status_word = m.group(1).strip(), m.group(2).strip()
        status_map = {"available": "AVAILABLE", "assigned": "ASSIGNED",
                      "under maintenance": "UNDER_MAINTENANCE", "damaged": "DAMAGED", "retired": "RETIRED"}
        count = svc.count_assets_by_category_and_status(category, status_map.get(status_word, "AVAILABLE"))
        plural = "" if category.endswith("s") else "(s)"
        return {"text": f"There are {count} {status_word} {category}{plural}.", "data": None}

    # ---- who has asset X ----
    m = re.search(r"who (?:has|holds|owns) (?:asset )?([a-z0-9\-]+)", q)
    if m:
        code = m.group(1).upper()
        row = svc.who_has_asset(code)
        if not row:
            return {"text": f"I couldn't find an asset with ID '{code}'.", "data": None}
        if row["assigned_to"]:
            return {"text": f"Asset {row['asset_code']} ({row['name']}) is assigned to {row['assigned_to']} in {row['department'] or 'an unassigned department'}.", "data": [row]}
        return {"text": f"Asset {row['asset_code']} ({row['name']}) is currently {row['status'].lower()} and not assigned to anyone.", "data": [row]}

    # ---- assets assigned to a department ----
    m = re.search(r"assets? (?:that are |which are )?assigned to (?:the )?([a-z ]+?)(?:\s+department)?[\.\?]?$", q) \
        or re.search(r"assigned to employees? in ([a-z ]+)", q)
    if m:
        dept = m.group(1).strip()
        rows = svc.assets_by_department(dept)
        if not rows:
            return {"text": f"No assets found for the '{dept}' department.", "data": []}
        text = f"Found {len(rows)} asset(s) in {dept}: " + ", ".join(
            f"{r['asset_code']} ({r['assigned_to'] or 'unassigned'})" for r in rows[:8])
        if len(rows) > 8:
            text += f", and {len(rows)-8} more."
        return {"text": text, "data": rows}

    # ---- pending / current maintenance ----
    if "maintenance" in q and ("pending" in q or "currently" in q or "in progress" in q or "under maintenance" in q):
        rows = svc.pending_maintenance()
        if not rows:
            return {"text": "No assets currently have pending maintenance.", "data": []}
        text = f"{len(rows)} asset(s) have pending maintenance: " + ", ".join(
            f"{r['asset_code']} ({r['status']})" for r in rows[:8])
        return {"text": text, "data": rows}

    # ---- repeated maintenance issues ----
    if "repeated" in q and "maintenance" in q:
        rows = svc.assets_with_repeated_maintenance()
        if not rows:
            return {"text": "No assets have repeated maintenance issues.", "data": []}
        text = f"{len(rows)} asset(s) have repeated maintenance records: " + ", ".join(
            f"{r['asset_code']} ({r['maintenance_count']}x)" for r in rows[:8])
        return {"text": text, "data": rows}

    # ---- high maintenance cost ----
    if "maintenance cost" in q or ("high" in q and "maintenance" in q and "cost" in q):
        rows = svc.assets_with_high_maintenance_cost()
        if not rows:
            return {"text": "No maintenance cost data is available yet.", "data": []}
        text = "Highest maintenance-cost assets: " + ", ".join(
            f"{r['asset_code']} ({_money(r['total_cost'])})" for r in rows)
        return {"text": text, "data": rows}

    # ---- licenses expiring ----
    if "license" in q and ("expire" in q or "expiring" in q or "renewal" in q):
        if "renew" in q:
            rows = svc.licenses_needing_renewal()
            if not rows:
                return {"text": "No licenses currently need renewal.", "data": []}
            text = f"{len(rows)} license(s) need renewal: " + ", ".join(
                f"{r['software_name']} (expires {r['expiry_date']})" for r in rows)
            return {"text": text, "data": rows}
        days = 30
        if "month" in q:
            days = 30
        rows = svc.licenses_expiring(days)
        if not rows:
            return {"text": f"No licenses expire within the next {days} days.", "data": []}
        text = f"{len(rows)} license(s) expire within {days} days: " + ", ".join(
            f"{r['software_name']} ({r['expiry_date']})" for r in rows)
        return {"text": text, "data": rows}

    # ---- department with highest asset cost ----
    if "highest" in q and ("asset cost" in q or "asset value" in q or "department" in q):
        row = svc.department_highest_asset_value()
        if not row:
            return {"text": "No department asset data available.", "data": None}
        return {"text": f"{row['name']} has the highest total asset value at {_money(row['total_value'])}.", "data": [row]}

    # ---- pending requests count ----
    if "pending request" in q or ("how many" in q and "request" in q):
        count = svc.pending_requests_count()
        return {"text": f"There are {count} pending asset request(s).", "data": None}

    # ---- unassigned / underutilized assets ----
    if "unassigned" in q or "underutilized" in q or "under-utilized" in q:
        rows = svc.underutilized_assets() if "underutil" in q else svc.unassigned_assets()
        if not rows:
            return {"text": "No matching assets found.", "data": []}
        text = f"{len(rows)} asset(s) found: " + ", ".join(r["asset_code"] for r in rows[:10])
        return {"text": text, "data": rows}

    # ---- warranty expiring ----
    if "warranty" in q and ("expir" in q):
        rows = svc.expiring_warranties()
        if not rows:
            return {"text": "No warranties are expiring soon.", "data": []}
        text = f"{len(rows)} asset(s) have warranties expiring soon: " + ", ".join(
            f"{r['asset_code']} ({r['warranty_end']})" for r in rows[:8])
        return {"text": text, "data": rows}

    # ---- total assets ----
    if "total assets" in q or "how many assets" in q:
        return {"text": f"There are {svc.total_assets_count()} total assets in the system.", "data": None}

    # ---- fallback ----
    return {
        "text": (
            "I can answer questions about assets, maintenance, licenses, requests and departments — "
            "for example: \"How many laptops are available?\", \"Who has asset LAP-1001?\", "
            "\"Which licenses expire next month?\", or \"Which department has the highest asset cost?\""
        ),
        "data": None,
    }
