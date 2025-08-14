"""
Routes for handling OAuth2 authentication.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import os
from core.config import APP_DOMAIN, logger
from core.lib.jwt import create_access_token
from core.models.user import User

oauth_router = APIRouter()

# --- Google OAuth ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = f"http://{APP_DOMAIN}/api/oauth/google/callback"

@oauth_router.get("/google/login", include_in_schema=False)
async def login_google(request: Request):
    return_url = request.query_params.get('return_url', '/')
    logger.info(f"Google login initiated. Return URL will be passed in state: {return_url}")
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={return_url}"  # Pass return_url in state
    )

@oauth_router.get("/google/callback", include_in_schema=False)
async def callback_google(request: Request, code: str, state: str):
    return_url = state
    logger.info(f"Received Google callback. State (return_url): {return_url}")
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_info = user_info_response.json()
        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            return HTMLResponse("<h1>Login Failed</h1><p>Could not retrieve email from Google.</p>", status_code=400)

        user = User.get_by_email(email)
        if not user:
            user = User.create(email=email, name=name)
            user.save()
            logger.info(f"Created new user for {email} via Google OAuth.")

        logger.info(f"USER OBJECT BEFORE TOKEN CREATION: {user.to_dict()}")
        jwt_payload = {"sub": user.email, "user_id": user.uid, "name": user.name}
        logger.info(f"JWT PAYLOAD BEFORE TOKEN CREATION: {jwt_payload}")
        session_token = create_access_token(data=jwt_payload)

        jwt_payload = {"sub": user.email, "user_id": user.uid, "name": user.name}
        session_token = create_access_token(data=jwt_payload)
        
        final_redirect_url = f"{return_url}?token={session_token}"
        logger.info(f"Redirecting back to gnosis-web: {final_redirect_url}")
        return RedirectResponse(final_redirect_url)


# --- GitHub OAuth ---
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
# GitHub doesn't use a static redirect_uri in the same way, but we can still use state
GITHUB_CALLBACK_URL = f"http://{APP_DOMAIN}/api/oauth/github/callback"

@oauth_router.get("/github/login", include_in_schema=False)
async def login_github(request: Request):
    return_url = request.query_params.get('return_url', '/')
    logger.info(f"GitHub login initiated. Return URL will be passed in state: {return_url}")
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&state={return_url}" # Pass return_url in state
    )

@oauth_router.get("/github/callback", include_in_schema=False)
async def callback_github(request: Request, code: str, state: str):
    return_url = state
    logger.info(f"Received GitHub callback. State (return_url): {return_url}")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        user_info_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_info_response.json()
        email = user_data.get("email")
        name = user_data.get("name", "")

        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            emails = emails_response.json()
            primary_email_obj = next((e for e in emails if e.get("primary")), None)
            if primary_email_obj:
                email = primary_email_obj.get("email")

        if not email:
            return HTMLResponse("<h1>Login Failed</h1><p>Could not retrieve primary email from GitHub.</p>", status_code=400)

        user = User.get_by_email(email)
        if not user:
            user = User.create(email=email, name=name)
            user.save()
            logger.info(f"Created new user for {email} via GitHub OAuth.")

        logger.info(f"USER OBJECT BEFORE TOKEN CREATION: {user.to_dict()}")
        jwt_payload = {"sub": user.email, "user_id": user.uid, "name": user.name}
        logger.info(f"JWT PAYLOAD BEFORE TOKEN CREATION: {jwt_payload}")
        session_token = create_access_token(data=jwt_payload)
        
        final_redirect_url = f"{return_url}?token={session_token}"
        logger.info(f"Redirecting back to gnosis-web: {final_redirect_url}")
        return RedirectResponse(final_redirect_url)