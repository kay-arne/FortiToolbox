from flask import Blueprint, render_template

dashboard_bp = Blueprint(
    'dashboard',
    __name__,
    template_folder='templates'
)

@dashboard_bp.route('/')
def index():
    """Rendert de hoofd layout shell."""
    return render_template('layout.html')

@dashboard_bp.route('/tool/dashboard')
def dashboard_tool():
    """Rendert de HTML partial voor de dashboard/welkomstpagina."""
    return render_template('dashboard.html')