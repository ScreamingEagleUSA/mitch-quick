# This blueprint is no longer needed as we're using Replit auth
# The authentication is now handled by replit_auth.py and routes.py
from flask import Blueprint, redirect, url_for, render_template, request, session, flash, jsonify
from flask_login import login_user, logout_user, current_user
from supabase_auth import verify_supabase_token, get_user_from_supabase
from models import User, db
import os
from supabase import create_client, Client

auth_bp = Blueprint('auth', __name__)

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")

if supabase_url and supabase_key:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Warning: Could not initialize Supabase client: {e}")
        supabase = None
else:
    print("Warning: Supabase credentials not found in environment variables")
    supabase = None

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

@auth_bp.route('/register', methods=['POST'])
def register_post():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    email = request.form.get('email')
    password = request.form.get('password')
    password2 = request.form.get('password2')
    
    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('auth.register'))
    
    if password != password2:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth.register'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('auth.register'))
    
    try:
        # Create user in Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('auth.register'))
            
    except Exception as e:
        print(f"Registration error: {e}")
        flash('Registration failed. Please try again.', 'error')
        return redirect(url_for('auth.register'))

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

@auth_bp.route('/verify-email')
def verify_email():
    """Handle email verification"""
    token = request.args.get('token')
    type_param = request.args.get('type')
    
    if token and type_param == 'signup':
        try:
            # Verify the email
            response = supabase.auth.verify_otp({
                "token_hash": token,
                "type": "signup"
            })
            
            if response.user:
                flash('Email verified successfully! You can now sign in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Email verification failed. Please try again.', 'error')
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            print(f"Email verification error: {e}")
            flash('Email verification failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))
    
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
