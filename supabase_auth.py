import os
import jwt
from functools import wraps
from flask import g, session, redirect, request, render_template, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin
from supabase import create_client, Client
from werkzeug.local import LocalProxy

from app import app, db
from models import User

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def get_user_from_supabase(user_id):
    """Get user from Supabase and sync with local database"""
    try:
        # Get user from Supabase
        response = supabase.auth.admin.get_user_by_id(user_id)
        user_data = response.user
        
        if not user_data:
            return None
            
        # Check if user exists in local database
        user = User.query.get(user_id)
        if not user:
            # Create new user in local database
            user = User()
            user.id = user_id
            user.email = user_data.email
            user.first_name = user_data.user_metadata.get('first_name', '')
            user.last_name = user_data.user_metadata.get('last_name', '')
            user.profile_image_url = user_data.user_metadata.get('avatar_url', '')
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user
            user.email = user_data.email
            user.first_name = user_data.user_metadata.get('first_name', user.first_name)
            user.last_name = user_data.user_metadata.get('last_name', user.last_name)
            user.profile_image_url = user_data.user_metadata.get('avatar_url', user.profile_image_url)
            db.session.commit()
            
        return user
    except Exception as e:
        print(f"Error getting user from Supabase: {e}")
        return None

def verify_supabase_token(token):
    """Verify JWT token from Supabase"""
    try:
        # Decode token without verification first to get user info
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get('sub')
        
        if not user_id:
            return None
            
        # Get user from database
        user = get_user_from_supabase(user_id)
        return user
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

def require_login(f):
    """Decorator to require user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Check for Supabase session
            access_token = session.get('supabase_access_token')
            if access_token:
                user = verify_supabase_token(access_token)
                if user:
                    login_user(user)
                else:
                    # Invalid token, clear session
                    session.clear()
                    flash('Your session has expired. Please log in again.', 'warning')
                    return redirect(url_for('auth.login'))
            else:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

# Auth blueprint
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/login.html')

@auth_bp.route('/login/callback')
def login_callback():
    """Handle Supabase auth callback"""
    try:
        # Get the access token from the URL parameters
        access_token = request.args.get('access_token')
        refresh_token = request.args.get('refresh_token')
        
        if not access_token:
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Store tokens in session
        session['supabase_access_token'] = access_token
        session['supabase_refresh_token'] = refresh_token
        
        # Verify token and get user
        user = verify_supabase_token(access_token)
        if user:
            login_user(user)
            next_url = session.pop("next_url", None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        print(f"Login callback error: {e}")
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/error')
def error():
    return render_template("403.html"), 403

def get_next_navigation_url(request):
    """Get the next URL for navigation"""
    is_navigation_url = request.headers.get('Sec-Fetch-Mode') == 'navigate' and request.headers.get('Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url 