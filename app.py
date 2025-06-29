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
    logging.info("Application will continue with limited functionality")

# Add database connection check function
def is_database_available():
    """Check if database is available"""
    try:
        with app.app_context():
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            return True
    except Exception as e:
        logging.warning(f"Database connection failed: {e}")
        return False

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Debug route to check environment
@app.route('/debug')
def debug():
    """Debug endpoint to check environment variables and database connection"""
    database_url = os.environ.get('DATABASE_URL')
    debug_info = {
        'supabase_url': bool(os.environ.get('SUPABASE_URL')),
        'supabase_anon_key': bool(os.environ.get('SUPABASE_ANON_KEY')),
        'database_url': bool(database_url),
        'database_url_preview': database_url[:50] + '...' if database_url and len(database_url) > 50 else database_url,
        'database_connected': False,
        'session_data': dict(session),
        'current_user_authenticated': current_user.is_authenticated if current_user else False
    }
    
    # Test database connection
    try:
        with app.app_context():
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            debug_info['database_connected'] = True
    except Exception as e:
        debug_info['database_error'] = str(e)
    
    return debug_info

@app.route('/debug/auth')
def debug_auth():
    """Debug endpoint to check authentication status"""
    access_token = session.get('supabase_access_token')
    
    debug_info = {
        'current_user_authenticated': current_user.is_authenticated if current_user else False,
        'current_user_id': current_user.id if current_user.is_authenticated else None,
        'current_user_email': current_user.email if current_user.is_authenticated else None,
        'has_supabase_token': bool(access_token),
        'session_keys': list(session.keys()),
        'supabase_client_initialized': bool(os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_ANON_KEY'))
    }
    
    if access_token:
        try:
            import jwt
            # Decode token without verification
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            debug_info['token_info'] = {
                'user_id': decoded.get('sub'),
                'email': decoded.get('email'),
                'exp': decoded.get('exp'),
                'iat': decoded.get('iat'),
                'aud': decoded.get('aud')
            }
        except Exception as e:
            debug_info['token_error'] = str(e)
    
    return debug_info

@app.route('/debug/db')
def debug_db():
    """Debug endpoint to check database connection"""
    database_url = os.environ.get('DATABASE_URL')
    
    debug_info = {
        'database_url_exists': bool(database_url),
        'database_url_preview': database_url[:50] + '...' if database_url and len(database_url) > 50 else database_url,
        'database_connected': False,
        'tables_exist': False,
        'connection_error': None
    }
    
    if not database_url:
        debug_info['connection_error'] = 'DATABASE_URL not set'
        return debug_info
    
    try:
        with app.app_context():
            from sqlalchemy import text
            
            # Test basic connection
            db.session.execute(text('SELECT 1'))
            debug_info['database_connected'] = True
            
            # Check if tables exist
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('auction', 'item', 'partner', 'item_partner', 'item_expense', 'item_sales')
            """))
            
            existing_tables = [row[0] for row in result.fetchall()]
            debug_info['existing_tables'] = existing_tables
            debug_info['tables_exist'] = len(existing_tables) > 0
            
    except Exception as e:
        debug_info['connection_error'] = str(e)
    
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
    # Try to load user from Supabase token if not already authenticated
    if not current_user.is_authenticated:
        access_token = session.get('supabase_access_token')
        if access_token:
            from supabase_auth import verify_supabase_token
            from flask_login import login_user
            user = verify_supabase_token(access_token)
            if user:
                login_user(user)
    
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

@app.route('/auth/auto-login')
def auto_login():
    """Manually authenticate user from Supabase token"""
    access_token = session.get('supabase_access_token')
    if not access_token:
        return {'error': 'No Supabase token found'}, 400
    
    from supabase_auth import verify_supabase_token
    from flask_login import login_user
    
    user = verify_supabase_token(access_token)
    if user:
        login_user(user)
        return {
            'success': True,
            'user_id': user.id,
            'user_email': user.email,
            'message': 'User authenticated successfully'
        }
    else:
        return {'error': 'Failed to verify token'}, 400

@app.route('/simple-test')
def simple_test():
    """Simple test that doesn't require database"""
    access_token = session.get('supabase_access_token')
    if not access_token:
        return {'error': 'No token found'}
    
    try:
        import jwt
        # Decode token without verification
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        user_id = decoded.get('sub')
        email = decoded.get('email')
        
        return {
            'success': True,
            'user_id': user_id,
            'email': email,
            'token_valid': True,
            'exp': decoded.get('exp'),
            'iat': decoded.get('iat')
        }
    except Exception as e:
        return {'error': f'Token decode failed: {str(e)}'}
