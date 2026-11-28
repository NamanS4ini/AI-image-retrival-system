from flask import Flask

from routes.local_routes import local_bp
from routes.main_routes import main_bp
from routes.online_routes import online_bp


def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)

    # Register route blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(local_bp)
    app.register_blueprint(online_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
