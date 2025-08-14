"""
Development-only routes for debugging and testing.
"""
from fastapi import APIRouter, HTTPException
from google.cloud import ndb
from core.models.user import User
from core.models.api_token import ApiToken
from core.models.base import get_ndb_client

dev_router = APIRouter()

@dev_router.post("/clear-database")
async def clear_database():
    """
    DANGEROUS: Deletes all User and ApiToken entities from the datastore.
    This is for development and testing only.
    """
    client = get_ndb_client()
    with client.context():
        ndb.delete_multi(User.query().fetch(keys_only=True))
        ndb.delete_multi(ApiToken.query().fetch(keys_only=True))
    return {"message": "All users and API tokens have been deleted."}
