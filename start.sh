#!/bin/bash
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate the virtual environment
source "$DIR/venv/bin/activate"

# Run the Flask application using Gunicorn for production
echo "Starting FortiToolbox server..."
gunicorn --workers 3 --bind 0.0.0.0:5001 "app:create_app()"
