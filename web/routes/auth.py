"""
Routes for handling email-based "magic link" authentication.
"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.models.user import User
from core.lib.util import generate_token
from core.lib.jwt import create_access_token
from core.config import logger, config

auth_router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

from core.lib.util import generate_token, email_user

@auth_router.post("/login")
async def email_login(request: Request, email: str = Form(...), return_url: str = Form(...)):
    """
    Handles email login. In dev, shows token entry page. In prod, sends email.
    """
    user = User.get_by_email(email)
    if not user:
        user = User.create(email=email, name=email.split('@')[0])
        logger.info(f"Creating new user object: {user.to_dict()}")
        user.save()
        logger.info(f"Saved new user with UID: {user.uid}")
    else:
        logger.info(f"Found existing user: {user.to_dict()}")
    
    # Generate and save a new mail token
    mail_token = generate_token(length=32)
    user.mail_token = mail_token
    user.save()

    # In development, we show the token entry page and log the token.
    if config.is_development:
        logger.info("="*40)
        logger.info(f"🔑 LOGIN TOKEN for {email}: {mail_token}")
        logger.info("="*40)
        return templates.TemplateResponse("token_entry.html", {
            "request": request,
            "email": email,
            "return_url": return_url
        })

    # In production, we email a link and show a confirmation page.
    else:
        login_link = f"http://{config.APP_DOMAIN}/api/auth/token?token={mail_token}&email={email}&return_url={return_url}"
        
        html_content = f"""
        <h1>Your Gnosis Login Link</h1>
        <p>Click the link below to log in:</p>
        <a href="{login_link}">Log in to Gnosis</a>
        <p>If you cannot click the link, copy and paste this URL into your browser:</p>
        <p>{login_link}</p>
        <p>For manual entry, your token is: <mark>{mail_token}</mark></p>
        """
        
        email_user(
            email=email,
            subject="Your Gnosis Login Link",
            html_content=html_content
        )
        
        return templates.TemplateResponse("check_email.html", {"request": request, "email": email})

@auth_router.get("/token")
async def verify_token_from_link(request: Request, email: str, token: str, return_url: str):
    """Verifies the mail_token from a link click."""
    # This reuses the same logic as the POST version
    return await verify_token(request, email, token, return_url)


@auth_router.post("/token")
async def verify_token(request: Request, email: str = Form(...), token: str = Form(...), return_url: str = Form(...)):
    """
    Verifies the mail_token submitted by the user.
    """
    user = User.get_by_email(email)
    
    if not user or user.mail_token != token:
        logger.warning(f"Invalid token submitted for user {email}")
        raise HTTPException(status_code=400, detail="Invalid token or email.")

    # The token is valid, clear it so it can't be reused.
    user.mail_token = ""
    user.save()

    # Create a real JWT session token
    jwt_payload = {"sub": user.email, "user_id": user.uid, "name": user.name}
    session_token = create_access_token(data=jwt_payload)
    
    # Redirect back to gnosis-web with the session token
    final_redirect_url = f"{return_url}?token={session_token}"
    logger.info(f"Email token verified for {email}. Redirecting to: {final_redirect_url}")
    
    # We need to return a response that will execute the redirect on the client side.
    # A simple HTML response with a meta refresh tag is a robust way to do this.
    return HTMLResponse(
        f'<html><head><meta http-equiv="refresh" content="0;url={final_redirect_url}" /></head><body>Redirecting...</body></html>'
    )
