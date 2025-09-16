from flask import Blueprint, render_template, request, jsonify
from config_manager import load_config, save_config
# CHANGE: Import the new, specific test functions
from tools.utils.shared_utils import clear_cache, test_api_connection, test_ssh_connection

config_tool_bp = Blueprint(
    'config_tool',
    __name__,
    template_folder='templates'
)

@config_tool_bp.route('/tool/config')
def config_tool():
    """Renders the HTML partial for the configuration tool."""
    current_config = load_config()
    return render_template('config.html', config=current_config)

# --- NEW ROUTES BELOW ---
@config_tool_bp.route('/test-api-config', methods=['POST'])
def test_api_config_route():
    """Tests only the API connection."""
    data = request.json
    is_success, message = test_api_connection(data)
    return jsonify({"success": is_success, "message": message})

@config_tool_bp.route('/test-ssh-config', methods=['POST'])
def test_ssh_config_route():
    """Tests only the SSH connection."""
    data = request.json
    is_success, message = test_ssh_connection(data)
    return jsonify({"success": is_success, "message": message})


@config_tool_bp.route('/save-config', methods=['POST'])
def save_config_route():
    """Saves the configuration submitted via the form."""
    try:
        data = request.json
        save_config(data)
        clear_cache()
        return jsonify({"success": True, "message": "Configuration saved successfully."})
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return jsonify({"success": False, "error": str(e)}), 500