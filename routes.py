from flask import session, render_template, redirect, url_for
from flask_login import current_user
from app import app, db
from replit_auth import require_login, make_replit_blueprint

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

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
        return render_template('landing.html')

@app.route('/dashboard')
@require_login # protected by Replit Auth
def dashboard():
    user = current_user
    return redirect(url_for('dashboard.index'))