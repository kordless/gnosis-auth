"""
Base model and NDB context management for gnosis-auth.
This implementation mirrors the proven decorator-based pattern from gnosis-wraith.
"""
import os
from functools import wraps
from google.cloud import ndb
from core.config import config, logger

def ndb_context_manager(func):
    """
    Decorator that creates a new NDB client and context for each call.
    This is the correct pattern for managing context in a web application.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        client = get_ndb_client()
        with client.context():
            return func(*args, **kwargs)
    return wrapper

def get_ndb_client():
    """
    Returns an NDB client configured for the current environment.
    """
    if not config.is_development:
        return ndb.Client()
    else:
        project = os.getenv('GOOGLE_CLOUD_PROJECT', 'gnosis-auth-dev')
        emulator_host = os.getenv('DATASTORE_EMULATOR_HOST')
        if not emulator_host:
            raise RuntimeError("DATASTORE_EMULATOR_HOST is not set for development.")
        return ndb.Client(project=project)

class BaseModel(ndb.Model):
    """Base model with common helper methods for NDB."""
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    def save(self):
        self.put()

    def delete(self):
        self.key.delete()
