import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Database configuration for Supabase PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable is required for Supabase connection")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        "pool_recycle": 300,
    }
    
    # eBay API Configuration
    EBAY_APP_ID = os.environ.get('EBAY_APP_ID', 'default_app_id')
    EBAY_CERT_ID = os.environ.get('EBAY_CERT_ID', 'default_cert_id')
    EBAY_DEV_ID = os.environ.get('EBAY_DEV_ID', 'default_dev_id')
    
    # Email Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'default_username')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'default_password')
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
