"""
API routes for managing resources like tokens.
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.security import OAuth2PasswordBearer
from google.cloud import ndb

from core.models.user import User
from core.models.api_token import ApiToken
from core.models.base import get_ndb_client
from core.schemas import ApiTokenSchema
from core.lib.jwt import verify_access_token

api_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

from core.config import logger

from core.config import logger

async def get_current_user_from_token(token: str = Depends(oauth2_scheme)):
    """
    A dependency that verifies a JWT from the Authorization header
    and returns the corresponding User object.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    logger.info("--- Verifying Token in API Dependency ---")
    payload = verify_access_token(token)
    if not payload:
        logger.error("API TOKEN VERIFICATION FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    logger.info(f"API TOKEN PAYLOAD: {payload}")
    user_uid = payload.get("user_id")
    if not user_uid:
        logger.error("user_id NOT FOUND in token payload.")
        raise HTTPException(status_code=401, detail="Invalid token payload")

    logger.info(f"Fetching user with UID from token: {user_uid}")
    user = User.get(user_uid)
    if not user:
        logger.error(f"USER NOT FOUND for UID: {user_uid}")
        raise HTTPException(status_code=401, detail="User not found")
    
    logger.info(f"API dependency successfully authenticated user: {user.email} with UID: {user.uid}")
    return user

@api_router.get("/tokens", response_model=List[ApiTokenSchema])
async def list_tokens(user: User = Depends(get_current_user_from_token)):
    """Lists all API tokens for the current user."""
    token_keys = [ndb.Key(ApiToken, uid) for uid in user.api_tokens]
    tokens = ndb.get_multi(token_keys)
    return [token.to_safe_dict() for token in tokens if token is not None]

@api_router.post("/tokens")
async def create_token(
    payload: Dict = Body(...),
    user: User = Depends(get_current_user_from_token)
):
    """Creates a new API token for the current user."""
    name = payload.get("name")
    expires_days_str = payload.get("expires_days")

    if not name:
        raise HTTPException(status_code=422, detail="Token name is required.")

    expires_days = None
    if expires_days_str and expires_days_str.isdigit():
        expires_days = int(expires_days_str)
    
    raw_token, new_api_token = ApiToken.create(
        user_uid=user.uid,
        name=name,
        expires_days=expires_days
    )
    
    new_api_token.save()
    
    user.api_tokens.append(new_api_token.uid)
    user.save()
    
    return {
        "new_token": raw_token, 
        "token_info": new_api_token.to_safe_dict()
    }

@api_router.post("/tokens/{token_uid}/revoke")
async def revoke_token(token_uid: str, user: User = Depends(get_current_user_from_token)):
    """Revokes (deactivates) an API token."""
    token = ApiToken.get(token_uid)
    
    if not token or token.user_uid != user.uid:
        raise HTTPException(status_code=404, detail="Token not found")
    
    token.active = False
    token.save()
    
    return {"message": "Token revoked successfully", "token_info": token.to_safe_dict()}

@api_router.delete("/tokens/{token_uid}")
async def delete_token(token_uid: str, user: User = Depends(get_current_user_from_token)):
    """Permanently deletes an API token."""
    token = ApiToken.get(token_uid)
    
    if not token or token.user_uid != user.uid:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Remove from user's token list
    if token_uid in user.api_tokens:
        user.api_tokens.remove(token_uid)
        user.save()
    
    # Delete the token
    token.delete()
    
    return {"message": "Token deleted successfully"}