# This blueprint is no longer needed as we're using Replit auth
# The authentication is now handled by replit_auth.py and routes.py
from flask import Blueprint, redirect, url_for

auth_bp = Blueprint('auth', __name__)

# Placeholder routes for backward compatibility - these will redirect to Replit auth
@auth_bp.route('/login')
def login():
    return redirect(url_for('replit_auth.login'))

@auth_bp.route('/logout')
def logout():
    return redirect(url_for('replit_auth.logout'))
