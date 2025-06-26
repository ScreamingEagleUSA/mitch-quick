import os
import logging
from flask import Flask, session, render_template, redirect, url_for
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Remove Replit-specific proxy configuration for Netlify
# app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
db = SQLAlchemy(app, model_class=Base)

# Add template functions
@app.template_global()
def current_time():
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M')

# Add last updated to context processor
@app.context_processor
def inject_last_updated():
    from datetime import datetime
    return {'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')}

# Create tables - but don't fail if database is unreachable
try:
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        logging.info("Database tables created")
except Exception as e:
    logging.warning(f"Could not create database tables during startup: {e}")
    logging.info("Tables may already exist or database may be temporarily unavailable")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Import and register blueprints
try:
    from supabase_auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    print("Auth blueprint registered successfully")
except Exception as e:
    print(f"Warning: Could not register auth blueprint: {e}")

# Register other blueprints - handle import errors gracefully
try:
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
    
    print("All blueprints registered successfully")
except Exception as e:
    print(f"Warning: Could not register some blueprints: {e}")
    print("Main routes will still work")

# Main routes
@app.route('/')
def index():
    # Use flask_login.current_user to check if current user is logged in or anonymous.
    if current_user.is_authenticated:
        # User is logged in, redirect to dashboard
        return redirect(url_for('dashboard.index'))
    else:
        # User is not logged in, show landing page
        return render_template('auth/landing.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Mitch Quick is running!"}
