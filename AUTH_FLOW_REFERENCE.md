# Authentication Flow Quick Reference

## Core Flow (from gnosis-wraith)

### 1. User Login Request
```
User → /login (GET) → Show login form with transaction_id
User → /login (POST) → Submit email + transaction_id
```

### 2. Email Token Generation
```python
# Generate secure token
mail_token = generate_token()  # Random 32-char string

# Build login link
login_link = f"https://{domain}/auth/token?mail_token={mail_token}&email={email}"

# Send email with link
email_user(email, subject="Login Link", html_content=template)
```

### 3. Token Verification
```
User clicks email link → /token?mail_token=X&email=Y
OR
User enters token manually → /token (POST)
```

### 4. Session Creation
```python
# After valid token
session['user_uid'] = user.uid
session['user_email'] = user.email
session['authenticated'] = True

# Rotate token for security
user.mail_token = generate_token()
```

### 5. JWT Generation (for AHP)
```python
# Exchange AHP token for JWT
POST /auth?token=ahp_xxxxx

# Response
{
    "access_token": "eyJ0eXAiOiJKV1...",
    "token_type": "Bearer",
    "expires_in": 1800,
    "scope": "read write"
}
```

## Key Components

### Anti-Bot Protection
- Transaction IDs for each form
- Honeypot password field
- Rate limiting on attempts

### Token Security
- Tokens rotate after each use
- Time-limited validity
- Secure random generation

### Session Management
- Cookie-based sessions
- Secure flag in production
- HttpOnly cookies

## FastAPI Adaptations Needed

### 1. Session Middleware
```python
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
```

### 2. Form Handling
```python
from fastapi import Form

@app.post("/login")
async def login(
    email: str = Form(...),
    transaction_id: str = Form(...),
    password: str = Form("")  # Honeypot
):
    # Process login
```

### 3. Auth Dependency
```python
async def get_current_user(request: Request):
    if 'user_email' in request.session:
        return User.get_by_email(request.session['user_email'])
    # Check API token headers
    # Return user or raise HTTPException(401)

@app.get("/protected")
async def protected(user = Depends(get_current_user)):
    return {"user": user.email}
```

### 4. Template Rendering
```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "transaction_id": generate_transaction_id()
    })
```

## Testing the Flow

1. **Test Login Form:**
   ```bash
   curl http://localhost:5000/login
   # Should show login form with transaction_id
   ```

2. **Test Email Send:**
   ```bash
   # With CONSOLE_OUTPUT=true, token appears in logs
   curl -X POST http://localhost:5000/login \
     -d "email=test@example.com&transaction_id=xxx"
   ```

3. **Test Token Verification:**
   ```bash
   # Use token from console/email
   curl "http://localhost:5000/token?mail_token=xxx&email=test@example.com"
   ```

4. **Test JWT Exchange:**
   ```bash
   # After creating API token in dashboard
   curl -X POST http://localhost:5000/auth \
     -d "token=ahp_xxxxx"
   ```

## Critical Files to Check

1. **gnosis-wraith/web/routes/auth.py** - Full Quart implementation
2. **gnosis-wraith/core/models/user.py** - User model with tokens
3. **gnosis-wraith/core/lib/util.py** - Token generation, email sending
4. **gnosis-wraith/web/templates/auth/** - HTML templates

Remember: The goal is to port the EXACT same flow, just adapted for FastAPI's patterns.
