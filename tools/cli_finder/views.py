from flask import Blueprint, render_template
import json
import os

cli_finder_bp = Blueprint(
    'cli_finder',
    __name__,
    template_folder='templates'
)

def load_commands():
    """Loads the CLI commands from the JSON file."""
    # Determine the path to the JSON file relative to this Python file
    file_path = os.path.join(os.path.dirname(__file__), 'fortios_commands.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading commands: {e}")
        return []

@cli_finder_bp.route('/tool/cli-finder')
def cli_finder_tool():
    """Renders the HTML partial for the CLI Command Finder tool."""
    commands = load_commands()
    return render_template('cli_finder.html', commands=commands)