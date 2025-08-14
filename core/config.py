"""
Gnosis Auth Configuration System
Environment-aware configuration supporting development, staging, and production modes
"""
import os
import logging
import sys
from pathlib import Path


class EnvironmentConfig:
    """Centralized environment configuration"""
    
    def __init__(self):
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
        print(f"[GnosisAuth] Initializing with ENVIRONMENT={self.ENVIRONMENT}")

        # Debug: print environment on initialization
        print(f"[GnosisAuth] Environment variables:")
        print(f"  ENVIRONMENT: {self.ENVIRONMENT}")
        print(f"  STORAGE_PATH: {os.getenv('STORAGE_PATH', 'Not set')}")
        print(f"  GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME', 'Not set')}")
        print(f"  EMAIL_PROVIDER: {os.getenv('EMAIL_PROVIDER', 'Not set')}")
        print(f"  TWILIO_ACCOUNT_SID: {'Set' if os.getenv('TWILIO_ACCOUNT_SID') else 'Not set'}")
        
    @property
    def is_development(self):
        return self.ENVIRONMENT == 'development'
    
    @property
    def is_staging(self):
        return self.ENVIRONMENT == 'staging'
    
    @property
    def is_production(self):
        return self.ENVIRONMENT == 'production'
    
    @property
    def use_cloud_storage(self):
        """Use cloud storage for staging and production"""
        return self.ENVIRONMENT in ['staging', 'production']
    
    @property
    def use_ndb_cloud(self):
        """Use Google Cloud Datastore for NDB models"""
        return self.use_cloud_storage
    
    @property
    def send_real_emails(self):
        """Only send real emails in production"""
        return self.ENVIRONMENT == 'production'
    
    @property
    def send_real_sms(self):
        """Only send real SMS in production"""
        return self.ENVIRONMENT == 'production'
    
    @property
    def console_output(self):
        """Show console output in dev and staging"""
        return self.ENVIRONMENT in ['development', 'staging']
    
    @property
    def enable_dev_endpoints(self):
        """Enable dev endpoints in development and staging"""
        return self.ENVIRONMENT in ['development', 'staging']
    
    @property
    def debug_mode(self):
        """Enable debug mode in development"""
        return self.is_development
    
    # Backward compatibility properties for existing gnosis services
    @property
    def DEV(self):
        """Backward compatibility for DEV checks"""
        return str(not self.is_production)
    
    @property
    def RUNNING_IN_CLOUD(self):
        """Backward compatibility for cloud checks"""
        return str(self.use_cloud_storage).lower()


# Global instance
config = EnvironmentConfig()

# Storage configuration
STORAGE_PATH = os.environ.get('STORAGE_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage'))
MODELS_DIR = os.path.join(STORAGE_PATH, "models")
USERS_DIR = os.path.join(STORAGE_PATH, "users")
LOGS_DIR = os.path.join(STORAGE_PATH, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "gnosis-auth.log")

# Ensure directories exist for local development
if config.is_development:
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

# Setup logging
logger = logging.getLogger("gnosis_auth")
logger.setLevel(logging.DEBUG if config.debug_mode else logging.INFO)

# Console handler
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG if config.debug_mode else logging.INFO)

# File handler
f_handler = logging.FileHandler(LOG_FILE)
f_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(formatter)
f_handler.setFormatter(formatter)

logger.addHandler(c_handler)
logger.addHandler(f_handler)

# Email configuration
EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'console')  # console, smtp, sendgrid
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

# From address for emails
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@gnosis-auth.local')
FROM_NAME = os.environ.get('FROM_NAME', 'Gnosis Auth')

# Twilio SMS configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# Google Cloud configuration
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'gnosis-auth-storage')
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', '')

# Security configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
TOKEN_LENGTH = int(os.environ.get('TOKEN_LENGTH', 32))
API_TOKEN_LENGTH = int(os.environ.get('API_TOKEN_LENGTH', 40))

# Rate limiting
MAX_EMAIL_ATTEMPTS = int(os.environ.get('MAX_EMAIL_ATTEMPTS', 5))
MAX_2FA_ATTEMPTS = int(os.environ.get('MAX_2FA_ATTEMPTS', 3))
EMAIL_COOLDOWN_MINUTES = int(os.environ.get('EMAIL_COOLDOWN_MINUTES', 5))

# Session configuration
SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 24))
API_TOKEN_EXPIRY_DAYS = int(os.environ.get('API_TOKEN_EXPIRY_DAYS', 365))

# Application configuration
APP_NAME = os.environ.get('APP_NAME', 'Gnosis Auth')
APP_DOMAIN = os.environ.get('APP_DOMAIN', 'localhost:5678')
APP_SUPPORT_EMAIL = os.environ.get('APP_SUPPORT_EMAIL', 'support@gnosis-auth.local')

logger.info(f"Gnosis Auth configuration initialized - Environment: {config.ENVIRONMENT}")
logger.info(f"Storage path: {STORAGE_PATH}")
logger.info(f"Cloud storage: {'Enabled' if config.use_cloud_storage else 'Disabled'}")
logger.info(f"Debug mode: {'Enabled' if config.debug_mode else 'Disabled'}")
