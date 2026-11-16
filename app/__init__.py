import logging
from flask import Flask, jsonify, render_template, request
from .config import Config
from .extensions import db, csrf, login_manager


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is required. Add a long random SECRET_KEY value to the project's .env file before starting UniSync.")
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    from .models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    from .routes.public import bp as public_bp
    from .routes.admin import bp as admin_bp
    from .routes.api import bp as api_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    from .cli import register
    register(app)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.errorhandler(404)
    def not_found(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(error="Not found"), 404
        return render_template("error.html", message="That page could not be found."), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled application error")
        if request.accept_mimetypes.best == "application/json":
            return jsonify(error="Internal server error"), 500
        return render_template("error.html", message="Something went wrong. Check the server log."), 500

    return app
