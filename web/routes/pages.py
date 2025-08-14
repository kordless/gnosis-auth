"""
Routes for serving essential HTML pages for the authentication flow.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# This assumes templates are configured in the main app.py
templates = Jinja2Templates(directory="web/templates")

pages_router = APIRouter()

@pages_router.get("/", include_in_schema=False)
async def root_redirect():
    """Redirects the root path to the login page."""
    return RedirectResponse(url="/login")

@pages_router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    """Serves the main login page which contains the OAuth options."""
    return templates.TemplateResponse("login.html", {"request": request})

# The /dashboard and /tokens pages have been removed from gnosis-auth.
# All user-facing UI will be handled by gnosis-web.
