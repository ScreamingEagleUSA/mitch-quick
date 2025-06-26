import os
import logging
from flask import Flask, session
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
