# --- THE DEFINITIVE FIX ---
# Import and apply monkey patching BEFORE anything else is imported.
# This is crucial and must be the very first code in your application.
from gevent import monkey
monkey.patch_all()
# --- END FIX ---

from flask import Flask
import os
import sys

# Add the project's root directory to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the blueprints from your tools
from tools.dashboard.views import dashboard_bp
from tools.proxmox_importer.views import proxmox_vm_importer_bp
from tools.config_tool.views import config_tool_bp
from tools.cli_finder.views import cli_finder_bp
from tools.scraper.views import scraper_bp

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    # CHANGE: Use a static secret key from environment variables.
    # This ensures that sessions survive a restart.
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_default_secret_key_change_me')

    # Register the blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(proxmox_vm_importer_bp)
    app.register_blueprint(config_tool_bp)
    app.register_blueprint(cli_finder_bp)
    app.register_blueprint(scraper_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    # For production, it's recommended to use a proper WSGI server like Gunicorn
    # The debug flag is now turned off for safety.
    app.run(debug=False, port=5001)