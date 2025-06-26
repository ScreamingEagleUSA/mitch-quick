from flask import session, render_template, redirect, url_for, request, flash
from flask_login import current_user
from app import app, db
from supabase_auth import require_login

@app.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
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
@require_login
def protected_test():
    """Test protected route"""
    return {
        'message': 'This is a protected route',
        'user_id': current_user.id,
        'user_email': current_user.email
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Mitch Quick is running!"}