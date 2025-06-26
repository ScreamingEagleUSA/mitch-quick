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

# Only create Supabase client if credentials are available
if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print(f"Supabase client initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize Supabase client: {e}")
        supabase = None
else:
    print("Warning: Supabase credentials not found in environment variables")
    supabase = None

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    try:
        return User.query.get(user_id)
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None

def create_or_update_user(user_data):
    """Create or update user in local database"""
    try:
        user_id = user_data.get('id')
        email = user_data.get('email')
        
        if not user_id or not email:
            return None
            
        # Check if user exists in local database
        try:
            user = User.query.get(user_id)
            if not user:
                # Create new user in local database
                user = User()
                user.id = user_id
                user.email = email
                user.first_name = user_data.get('user_metadata', {}).get('first_name', '')
                user.last_name = user_data.get('user_metadata', {}).get('last_name', '')
                user.profile_image_url = user_data.get('user_metadata', {}).get('avatar_url', '')
                db.session.add(user)
            else:
                # Update existing user
                user.email = email
                user.first_name = user_data.get('user_metadata', {}).get('first_name', user.first_name)
                user.last_name = user_data.get('user_metadata', {}).get('last_name', user.last_name)
                user.profile_image_url = user_data.get('user_metadata', {}).get('avatar_url', user.profile_image_url)
            
            db.session.commit()
            return user
        except Exception as db_error:
            print(f"Database error creating/updating user: {db_error}")
            # If database fails, create a temporary user object
            from flask_login import UserMixin
            class TempUser(UserMixin):
                def __init__(self, user_id, email, user_data):
                    self._id = user_id
                    self._email = email
                    self._first_name = user_data.get('user_metadata', {}).get('first_name', '')
                    self._last_name = user_data.get('user_metadata', {}).get('last_name', '')
                    self._profile_image_url = user_data.get('user_metadata', {}).get('avatar_url', '')
                
                @property
                def id(self):
                    return self._id
                
                @property
                def email(self):
                    return self._email
                
                @property
                def first_name(self):
                    return self._first_name
                
                @property
                def last_name(self):
                    return self._last_name
                
                @property
                def profile_image_url(self):
                    return self._profile_image_url
                
                @property
                def is_authenticated(self):
                    return True
                
                @property
                def is_active(self):
                    return True
                
                @property
                def is_anonymous(self):
                    return False
            
            return TempUser(user_id, email, user_data)
            
    except Exception as e:
        print(f"Error creating/updating user: {e}")
        return None

def verify_supabase_token(token):
    """Verify JWT token from Supabase"""
    try:
        # Decode token without verification to get user info
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get('sub')
        
        if not user_id:
            print("No user ID found in token")
            return None
            
        # Extract user data from token
        user_data = {
            'id': user_id,
            'email': decoded.get('email'),
            'user_metadata': decoded.get('user_metadata', {})
        }
        
        # Create or update user in local database
        user = create_or_update_user(user_data)
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

@auth_bp.route('/register')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')

@auth_bp.route('/verify-email')
def verify_email():
    """Handle email verification"""
    token = request.args.get('token')
    type = request.args.get('type')
    
    if type == 'signup' and token:
        try:
            # Verify the email
            if supabase:
                response = supabase.auth.verify_otp({
                    "token_hash": token,
                    "type": "signup"
                })
                if response.user:
                    flash('Email verified successfully! You can now sign in.', 'success')
                    return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"Email verification error: {e}")
            flash('Email verification failed. Please try again.', 'error')
    
    flash('Invalid verification link.', 'error')
    return redirect(url_for('auth.login'))

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