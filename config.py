import os

class Config:
    SECRET_KEY = os.environ.get('SESSION_SECRET') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///mitchquick.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
