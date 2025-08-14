"""
API Token model for Gnosis Auth (NDB version).
"""
import uuid
import hashlib
import datetime
from google.cloud import ndb
from .base import BaseModel, ndb_context_manager
from core.lib.util import generate_token

class ApiToken(BaseModel):
    """Represents a long-lived API token for a user."""
    user_uid = ndb.StringProperty(required=True)
    name = ndb.StringProperty(required=True)
    token_hash = ndb.StringProperty(required=True)
    token_display = ndb.StringProperty(required=True)
    active = ndb.BooleanProperty(default=True)
    expires = ndb.DateTimeProperty()

    @property
    def uid(self):
        return self.key.id()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _mask_token(token: str) -> str:
        return f"{token[:8]}...{token[-4:]}"

    @classmethod
    def create(cls, user_uid: str, name: str, expires_days: int = None):
        raw_token = f"ahp_{generate_token(48)}"
        uid = str(uuid.uuid4())
        token_key = ndb.Key(ApiToken, uid)
        
        expires_dt = None
        if expires_days:
            expires_dt = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)

        new_token = cls(
            key=token_key,
            user_uid=user_uid,
            name=name,
            token_hash=cls._hash_token(raw_token),
            token_display=cls._mask_token(raw_token),
            expires=expires_dt
        )
        return raw_token, new_token

    @classmethod
    def get(cls, uid):
        """Retrieves a token by its UID."""
        if not uid:
            return None
        return ndb.Key(cls, uid).get()

    @classmethod
    def get_by_token(cls, token_value: str):
        token_hash = cls._hash_token(token_value)
        token = cls.query(cls.token_hash == token_hash).get()
        if token and token.is_valid():
            return token
        return None

    def is_valid(self) -> bool:
        if not self.active:
            return False
        if self.expires and self.expires < datetime.datetime.utcnow():
            return False
        return True

    def to_safe_dict(self) -> dict:
        return {
            "uid": self.uid,
            "user_uid": self.user_uid,
            "name": self.name,
            "token_display": self.token_display,
            "created": self.created.isoformat(),
            "expires": self.expires.isoformat() if self.expires else None,
            "active": self.active
        }
