import os
from datetime import timedelta
from flask import Flask, render_template, session

from config import Config
from database import db as database
from utils.security import current_user, get_user_permissions

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.asset_routes import asset_bp
from routes.employee_routes import employee_bp
from routes.department_routes import department_bp
from routes.request_routes import request_bp
from routes.maintenance_routes import maintenance_bp
from routes.license_routes import license_bp
from routes.report_routes import report_bp
from routes.admin_routes import admin_bp
from routes.notification_routes import notification_bp
from routes.ai_routes import ai_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(days=7)

    database.init_app(app)

    for bp in (auth_bp, dashboard_bp, asset_bp, employee_bp, department_bp, request_bp,
               maintenance_bp, license_bp, report_bp, admin_bp, notification_bp, ai_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        user = current_user()
        perms = get_user_permissions(user) if user else set()
        return {"logged_in_user": user, "user_permissions": perms}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
