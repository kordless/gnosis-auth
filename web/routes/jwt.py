"""
Routes for JWT token exchange and JWKS.
"""
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from core.lib.jwt import create_access_token, get_jwks, verify_access_token
from core.models.api_token import ApiToken
from core.models.user import User
import os

jwt_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

@jwt_router.get("/api/verify")
async def verify_token_endpoint(token: str = Depends(oauth2_scheme)):
    """
    Verifies a JWT token provided in the Authorization header.
    Used by other services to validate a user's session token.
    """
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

@jwt_router.post("/auth")
async def exchange_token(token: str = Form(...)):
    """
    Exchanges a valid AHP token for a short-lived JWT.
    """
    ahp_token = ApiToken.get_by_token(token)
    if not ahp_token or not ahp_token.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive AHP token")

    user = User.get(ahp_token.user_uid)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # TODO: Add scope handling
    scopes = ["read", "write"]

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.uid, "scopes": scopes}
    )
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(os.environ.get("JWT_EXPIRATION_MINUTES", 30)) * 60
    }

@jwt_router.get("/.well-known/jwks.json")
async def jwks():
    """
    Serves the public key in JWKS format for JWT verification.
    """
    return JSONResponse(content=get_jwks())
