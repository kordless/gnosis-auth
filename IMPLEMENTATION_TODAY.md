# Gnosis Auth: FastAPI Implementation Plan - TODAY

## URGENT: 3-Part Implementation Plan for Today

### Part 1: Core Authentication Setup (2 hours)

**Goal:** Get basic passwordless email authentication working with FastAPI

1. **Update FastAPI app.py with session support:**
   - Add SessionMiddleware for cookie-based sessions
   - Configure session secret and settings
   - Set up proper CORS for auth cookies

2. **Port core models from gnosis-wraith:**
   - Copy `core/models/user.py` from gnosis-wraith
   - Copy `core/models/api_token.py` from gnosis-wraith
   - Copy `core/models/base.py` for local storage support
   - Ensure Transaction model for anti-bot protection

3. **Port authentication utilities:**
   - Copy `core/lib/util.py` from gnosis-wraith
   - Focus on: `email_user()`, `generate_token()`, `random_string()`
   - Set up email configuration in .env

4. **Create FastAPI auth routes:**
   - Replace placeholder routes in `web/routes/__init__.py`
   - Implement `/api/auth/login` (GET/POST)
   - Implement `/api/auth/token` (GET/POST) 
   - Implement `/api/auth/logout`
   - Create auth dependencies for `login_required`

### Part 2: JWT Token Exchange for AHP (1.5 hours)

**Goal:** Implement the key feature - exchanging AHP tokens for JWTs

1. **Set up JWT infrastructure:**
   - Generate RSA key pair for JWT signing
   - Store keys in `config/keys/` directory
   - Configure JWT settings in environment

2. **Implement token exchange endpoint:**
   - `POST /auth` - Exchange AHP_TOKEN for JWT
   - Validate AHP token against stored tokens
   - Generate signed JWT with proper claims
   - Return bearer token with expiration

3. **Implement JWKS endpoint:**
   - `GET /.well-known/jwks.json` - Serve public key
   - Standard JWKS format for federated services
   - Include key ID, algorithm, use parameters

4. **Create validation utilities:**
   - JWT generation with RS256
   - Token validation helpers
   - Scope checking utilities

### Part 3: Web UI and API Token Management (1.5 hours)

**Goal:** Basic web interface for humans to get tokens

1. **Port HTML templates from gnosis-wraith:**
   - Copy `web/templates/auth/` directory
   - Update templates for FastAPI/Jinja2
   - Ensure brand customization works

2. **Implement pages router:**
   - `/` - Landing/home page
   - `/login` - Login page (render template)
   - `/dashboard` - User dashboard
   - `/tokens` - API token management

3. **API token management endpoints:**
   - `GET /api/tokens` - List user's tokens
   - `POST /api/tokens` - Create new token
   - `DELETE /api/tokens/{id}` - Revoke token

4. **Basic testing checklist:**
   - User can log in via email
   - Email contains working login link
   - User receives JWT after login
   - API tokens can be created/managed
   - JWKS endpoint serves public key

---

## Implementation Notes for Gemini:

- Start with Part 1 to get basic auth working
- Copy liberally from gnosis-wraith - the patterns are proven
- Focus on core functionality, skip SMS/2FA for now
- Use local storage mode for development speed
- Test each part before moving to the next

## Key Files to Copy/Reference from gnosis-wraith:

1. **Models:**
   - `gnosis-wraith/core/models/user.py`
   - `gnosis-wraith/core/models/api_token.py` 
   - `gnosis-wraith/core/models/base.py`

2. **Auth Logic:**
   - `gnosis-wraith/web/routes/auth.py` (Quart version to adapt)
   - `gnosis-wraith/core/lib/util.py` (utilities)

3. **Templates:**
   - `gnosis-wraith/web/templates/auth/` directory

## FastAPI-Specific Changes Needed:

1. **Session Management:**
   ```python
   from starlette.middleware.sessions import SessionMiddleware
   app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
   ```

2. **Request Handling:**
   ```python
   # Quart: await request.form
   # FastAPI: Use Form() dependencies or Pydantic models
   ```

3. **Auth Dependencies:**
   ```python
   from fastapi import Depends, HTTPException
   
   async def get_current_user(request: Request):
       # Check session or API token
       # Return user or raise HTTPException
   
   @app.get("/protected")
   async def protected_route(user = Depends(get_current_user)):
       return {"user": user}
   ```

---

## Environment Variables Needed:

```bash
# Session
SECRET_KEY=generate-a-long-random-string

# Email (for dev, use console output)
CONSOLE_OUTPUT=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@gnosis-auth.local

# JWT
JWT_PRIVATE_KEY_PATH=config/keys/private_key.pem
JWT_PUBLIC_KEY_PATH=config/keys/public_key.pem
JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=30

# App
APP_DOMAIN=localhost:5000
BRAND=Gnosis Auth
```

---

This plan focuses on getting a working authentication system TODAY. The key is to reuse the proven patterns from gnosis-wraith while adapting them to FastAPI's style.
