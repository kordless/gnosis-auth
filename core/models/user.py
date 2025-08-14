"""
User model for Gnosis Auth (NDB version).
"""
import uuid
from google.cloud import ndb
from .base import BaseModel, ndb_context_manager

class User(BaseModel):
    """Represents a user account in the Datastore."""
    email = ndb.StringProperty(required=True)
    name = ndb.StringProperty()
    active = ndb.BooleanProperty(default=True)
    mail_token = ndb.StringProperty()
    api_tokens = ndb.StringProperty(repeated=True)

    @property
    def uid(self):
        return self.key.id() if self.key else None

    @classmethod
    def get_by_email(cls, email):
        """Finds a user by their email address using an NDB query."""
        return cls.query(cls.email == email).get()

    @classmethod
    def get(cls, uid):
        """Retrieves a user by their UID."""
        if not uid:
            return None
        return ndb.Key(cls, uid).get()

    @staticmethod
    def create(email: str, name: str = ""):
        """Creates a new User entity with a generated string UID."""
        uid = str(uuid.uuid4())
        user_key = ndb.Key(User, uid)
        new_user = User(
            key=user_key,
            email=email,
            name=name
        )
        return new_user