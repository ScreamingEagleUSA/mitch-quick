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
        logging.info("Database tables created successfully")
except Exception as e:
    logging.warning(f"Could not create database tables during startup: {e}")
    logging.info("Tables may already exist or database may be temporarily unavailable")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Debug route to check environment
@app.route('/debug')
def debug():
    """Debug endpoint to check environment variables and database connection"""
    debug_info = {
        'supabase_url': bool(os.environ.get('SUPABASE_URL')),
        'supabase_anon_key': bool(os.environ.get('SUPABASE_ANON_KEY')),
        'database_url': bool(os.environ.get('DATABASE_URL')),
        'database_connected': False,
        'session_data': dict(session),
        'current_user_authenticated': current_user.is_authenticated if current_user else False
    }
    
    # Test database connection
    try:
        with app.app_context():
            db.session.execute('SELECT 1')
            debug_info['database_connected'] = True
    except Exception as e:
        debug_info['database_error'] = str(e)
    
    return debug_info

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
        return render_template('landing.html')

@app.route('/test-auth')
def test_auth():
    """Test authentication status"""
    return {
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'user_email': current_user.email if current_user.is_authenticated else None,
        'session_keys': list(session.keys()),
        'has_supabase_token': 'supabase_access_token' in session
    }

@app.route('/protected-test')
def protected_test():
    """Test protected route"""
    from supabase_auth import require_login
    
    @require_login
    def protected_function():
        return {
            'message': 'This is a protected route',
            'user_id': current_user.id,
            'user_email': current_user.email
        }
    
    return protected_function()

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Mitch Quick is running!"}
