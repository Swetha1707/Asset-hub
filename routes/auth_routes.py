import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_one, execute
from utils.security import current_user, log_activity, login_required

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if session.get("role_name") == "EMPLOYEE":
        return redirect(url_for("request.requests_page"))

    return redirect(url_for("dashboard.dashboard_home"))
@auth_bp.route("/add-admin", methods=["GET", "POST"])
@login_required
def add_admin():
    user = current_user()

    if user["role_name"] not in ["ADMIN", "SUPER_ADMIN"]:
        return "Forbidden", 403

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        if not full_name or not username or not email or not password:
            errors.append("Please fill in all required fields.")

        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if query_one("SELECT id FROM users WHERE username=%s", (username,)):
            errors.append("Username is already taken.")

        if query_one("SELECT id FROM users WHERE email=%s", (email,)):
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("add_admin.html")

        role = query_one("SELECT id FROM roles WHERE name='ADMIN'")

        if not role:
            flash("ADMIN role not found.", "error")
            return render_template("add_admin.html")

        pw_hash = generate_password_hash(password)

        execute(
            """
            INSERT INTO users
            (full_name, username, email, phone, password_hash, role_id)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                full_name,
                username,
                email,
                phone or None,
                pw_hash,
                role["id"]
            )
        )

        log_activity(
            user,
            "CREATE_ADMIN",
            "AUTH",
            f"Created admin account: {username}"
        )

        flash("Admin created successfully.", "success")
        return redirect(url_for("auth.add_admin"))

    return render_template("add_admin.html")
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        from database.db import query_all
        depts = query_all("SELECT id, name FROM departments ORDER BY name")
        return render_template("register.html", departments=depts)

    data = request.form
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    department_id = data.get("department_id") or None
    employee_id = data.get("employee_id", "").strip()

    errors = []
    if not full_name or not username or not email or not password:
        errors.append("Please fill in all required fields.")
    if not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    if not errors:
        if query_one("SELECT id FROM users WHERE username=%s", (username,)):
            errors.append("Username is already taken.")
        if query_one("SELECT id FROM users WHERE email=%s", (email,)):
            errors.append("An account with this email already exists.")
        if employee_id and query_one("SELECT id FROM users WHERE employee_id=%s", (employee_id,)):
            errors.append("Employee ID is already registered.")

    if errors:
        from database.db import query_all
        depts = query_all("SELECT id, name FROM departments ORDER BY name")
        for e in errors:
            flash(e, "error")
        return render_template("register.html", departments=depts, form=data)

    role = query_one("SELECT id FROM roles WHERE name='EMPLOYEE'")
    pw_hash = generate_password_hash(password)
    result = execute(
        """INSERT INTO users (full_name, username, email, phone, password_hash, employee_id, department_id, role_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (full_name, username, email, phone, pw_hash, employee_id or None, department_id, role["id"]),
    )
    # Also create matching employee profile
    execute(
        """INSERT INTO employees (user_id, employee_code, name, email, phone, department_id, status)
           VALUES (%s,%s,%s,%s,%s,%s,'ACTIVE')""",
        (result["lastrowid"], employee_id or f"EMP-{result['lastrowid']:04d}", full_name, email, phone, department_id),
    )
    flash("Registration successful! You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    identifier = request.form.get("identifier", "").strip()
    password = request.form.get("password", "")
    remember = request.form.get("remember")

    user = query_one(
        """SELECT u.*, r.name as role_name FROM users u
           JOIN roles r ON u.role_id = r.id
           WHERE (u.username=%s OR u.email=%s)""",
        (identifier, identifier),
    )

    if not user or not check_password_hash(user["password_hash"], password):
        log_activity(user, "LOGIN_FAILED", "AUTH", f"Failed login attempt for '{identifier}'", status="FAILED")
        flash("Invalid username/email or password.", "error")
        return render_template("login.html")

    if not user["is_active"]:
        flash("Your account has been deactivated. Contact an administrator.", "error")
        return render_template("login.html")

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role_name"] = user["role_name"]
    if remember:
        session.permanent = True

    log_activity(user, "LOGIN", "AUTH", "User logged in")
    if user["role_name"] == "EMPLOYEE":
        return redirect(url_for("request.requests_page"))

    return redirect(url_for("dashboard.dashboard_home"))

@auth_bp.route("/logout")
@login_required
def logout():
    user = current_user()
    log_activity(user, "LOGOUT", "AUTH", "User logged out")
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        db_user = query_one(
            "SELECT password_hash FROM users WHERE id=%s",
            (user["id"],)
        )

        if not check_password_hash(
            db_user["password_hash"],
            current_password
        ):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("auth.profile"))

        if len(new_password) < 8:
            flash(
                "New password must be at least 8 characters long.",
                "error"
            )
            return redirect(url_for("auth.profile"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return redirect(url_for("auth.profile"))

        if check_password_hash(
            db_user["password_hash"],
            new_password
        ):
            flash(
                "New password cannot be the same as current password.",
                "error"
            )
            return redirect(url_for("auth.profile"))

        new_hash = generate_password_hash(new_password)

        execute(
            "UPDATE users SET password_hash=%s WHERE id=%s",
            (new_hash, user["id"])
        )

        log_activity(
            user,
            "PASSWORD_CHANGE",
            "AUTH",
            "User changed their password"
        )

        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(url_for("auth.profile"))

    return render_template("profile.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("If an account exists with that email, password reset instructions have been noted by an administrator (demo mode — no email server configured).", "success")
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")
