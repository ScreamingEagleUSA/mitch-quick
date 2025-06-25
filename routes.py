from flask import session, render_template, redirect, url_for
from flask_login import current_user
from app import app, db
from replit_auth import require_login, make_replit_blueprint

# Register Replit auth blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Register other blueprints
from blueprints.dashboard import dashboard_bp
from blueprints.auctions import auctions_bp
from blueprints.items import items_bp
from blueprints.partners import partners_bp
from blueprints.reports import reports_bp
from blueprints.expenses import expenses_bp

app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(auctions_bp, url_prefix='/auctions')
app.register_blueprint(items_bp, url_prefix='/items')
app.register_blueprint(partners_bp, url_prefix='/partners')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(expenses_bp, url_prefix='/expenses')

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    # Use flask_login.current_user to check if current user is logged in or anonymous.
    if current_user.is_authenticated:
        # User is logged in, redirect to dashboard
        return redirect(url_for('dashboard.index'))
    else:
        # User is not logged in, show landing page
        return render_template('auth/landing.html')