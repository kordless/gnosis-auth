# Gnosis Federation: Complete Implementation Plan

This document outlines the comprehensive implementation plan for creating the federated Gnosis ecosystem with centralized authentication.

---

## Part 1: The Vision - Agentic Hypercall Protocol (AHP)

### 1.1. The Problem: The Tyranny of the SDK
The current AI landscape fragments into walled gardens, with each service demanding proprietary SDKs. This creates a "tyranny of the SDK" that stifles innovation and locks users into specific ecosystems.

### 1.2. The Solution: The Primal Protocol
The AHP rejects this complexity through radical simplification: **It's Just The URL.**

- **All actions are GET requests**
- **Tools are paths** 
- **Parameters are query strings**

This ensures any agent capable of constructing a URL can participate in the ecosystem.

### 1.3. Service Discovery
Service discovery and endpoint documentation will be handled through `https://ahp.nuts.services` as the canonical reference for the protocol and available services.

### 1.4. The Federated World
The vision is a constellation of sovereign, interoperable nodes: `gnosis-ocr`, `gnosis-wraith`, `gnosis-ahp`, and future services. The common trust anchor is the centralized authentication service at `auth.nuts.services`.

---

## Part 2: Implementation of `auth.nuts.services`

### 2.1. New Standalone Authentication Service

Create a completely new, standalone service that will be the federation's authentication hub.

**Core Responsibilities:**
- Token exchange (long-lived AHP_TOKEN → short-lived JWT)
- Key management for JWT signing
- Public key distribution via JWKS
- User authentication UI
- Account management interface

### 2.2. Service Architecture

```
auth.nuts.services/
├── app.py                 # Main FastAPI application
├── models/
│   ├── user.py           # User model (simplified for auth only)
│   └── ahp_token.py      # AHP token management
├── routes/
│   ├── auth.py           # Authentication endpoints
│   ├── pages.py          # Web UI routes
│   └── api.py            # API endpoints
├── templates/
│   ├── login.html        # Login page
│   ├── dashboard.html    # User dashboard
│   └── tokens.html       # Token management
├── static/               # CSS/JS assets
└── config/
    ├── keys/             # JWT signing keys
    └── settings.py       # Configuration
```

### 2.3. Core Endpoints

**Authentication API:**
- `POST /auth` - Exchange AHP_TOKEN for JWT bearer token
- `GET /.well-known/jwks.json` - Public key for JWT verification
- `POST /validate` - Validate JWT tokens (for services)

**Web UI:**
- `GET /` - Landing/login page
- `GET /login` - Login form
- `POST /login` - Process login
- `GET /dashboard` - User dashboard with token management
- `GET /tokens` - Token management interface

**Token Management API:**
- `GET /api/tokens` - List user's AHP tokens
- `POST /api/tokens` - Create new AHP token
- `DELETE /api/tokens/{token_id}` - Revoke AHP token

### 2.4. Implementation Steps

#### Step 1: Initialize New Service
1. Create new directory: `gnosis-auth`
2. Initialize FastAPI application with Quart (to match existing stack)
3. Set up basic project structure
4. Configure deployment pipeline

#### Step 2: Core Authentication Logic
1. **Generate JWT signing keys:**
   ```bash
   openssl genrsa -out private_key.pem 2048
   openssl rsa -in private_key.pem -pubout -out public_key.pem
   ```
2. **Implement `/auth` endpoint:**
   - Accept `token` query parameter (the AHP_TOKEN)
   - Validate against stored tokens
   - Generate signed JWT with `agent_id`, `exp`, `iat`, `scopes`
   - Return short-lived bearer token (15-30 minutes)

3. **Implement `/.well-known/jwks.json`:**
   - Serve public key in standard JWKS format
   - Include key ID, algorithm, use parameters

#### Step 3: User Management
1. **Simplified User Model:**
   ```python
   class User:
       email: str
       name: str  
       created: datetime
       active: bool = True
       ahp_tokens: List[AHPToken] = []
   ```

2. **AHP Token Model:**
   ```python
   class AHPToken:
       token_id: str
       user_email: str
       token_value: str  # The actual AHP_TOKEN
       name: str
       scopes: List[str] = ['read', 'write']  # Default scopes
       created: datetime
       expires: Optional[datetime]
       last_used: Optional[datetime]
       active: bool = True
   ```

#### Step 4: Web UI Implementation
1. **Login System:**
   - Email-based passwordless authentication
   - Use existing email token pattern from gnosis-wraith
   - Simple, clean UI focused on developers/power users

2. **Dashboard:**
   - List active AHP tokens
   - Create new tokens with custom names/scopes
   - Revoke tokens
   - View usage statistics

3. **Token Management:**
   - Clear display of token values (one-time show after creation)
   - Copy-to-clipboard functionality
   - Scope selection interface

#### Step 5: Security Implementation
1. **AHP Token Generation:**
   - Use cryptographically secure random generation
   - Format: `ahp_` + 32-byte base64url encoded string
   - Store hashed versions in database

2. **JWT Configuration:**
   - Algorithm: RS256 (RSA with SHA-256)
   - Payload: `{"sub": "user_email", "agent_id": "unique_id", "scopes": ["read", "write"], "exp": timestamp, "iat": timestamp}`
   - Short expiration (15-30 minutes)

3. **Rate Limiting:**
   - Implement per-IP rate limiting on auth endpoints
   - Separate limits for web UI vs API access

---

## Part 3: Service Integration

### 3.1. Update Existing Services

**For each service (gnosis-ahp, gnosis-ocr, gnosis-wraith):**

1. **Remove local auth endpoints:**
   - Remove `/auth` endpoints from services
   - Keep existing token validation decorators but update logic

2. **Update token validation:**
   ```python
   async def verify_federation_token(token: str):
       # Fetch public key from auth.nuts.services/.well-known/jwks.json
       # Verify JWT signature
       # Extract user info from claims
       # Return user context
   ```

3. **Scope validation:**
   - Each service defines its own required scopes
   - Validate JWT contains required scopes for endpoint access
   - Fail gracefully with clear error messages

### 3.2. Service-Specific Scopes

**Recommended scope patterns:**
- `gnosis-ahp:read` - Read access to AHP service
- `gnosis-ahp:write` - Write access to AHP service  
- `gnosis-ocr:read` - Read access to OCR service
- `gnosis-ocr:process` - Process documents via OCR
- `gnosis-wraith:read` - Read access to Wraith service
- `gnosis-wraith:crawl` - Perform crawling operations

**Default scopes:** `["read"]` for all services, users can request additional scopes as needed.

---

## Part 4: Migration Strategy

### 4.1. Backward Compatibility
1. **Dual Authentication Support:**
   - Services accept both old API tokens and new federation JWTs
   - Gradual migration over 3-6 months
   - Clear deprecation timeline for old tokens

2. **User Migration:**
   - Import existing users from gnosis-wraith to auth.nuts.services
   - Generate initial AHP tokens for existing users
   - Email migration instructions with new token access

### 4.2. Rollout Plan
1. **Phase 1:** Deploy auth.nuts.services with basic functionality
2. **Phase 2:** Update one service (gnosis-ahp) to use federation auth
3. **Phase 3:** Migrate remaining services
4. **Phase 4:** Deprecate local authentication systems
5. **Phase 5:** Remove legacy auth code

---

## Part 5: Development Deliverables

### 5.1. New Repository: `gnosis-auth`
- Complete FastAPI/Quart application
- User management system
- Token management system  
- Web UI for authentication and token management
- API documentation
- Deployment configuration (Docker, Cloud Run, etc.)

### 5.2. Service Updates
- Updated authentication decorators for all services
- Migration scripts for existing users
- Updated API documentation reflecting new auth flow

### 5.3. Documentation
- Developer guide for federation authentication
- Migration guide for existing users
- API reference for all endpoints
- Troubleshooting guide

---

## Part 6: Technical Specifications

### 6.1. Environment Variables
```bash
# JWT Configuration
JWT_PRIVATE_KEY_PATH=/config/keys/private_key.pem
JWT_PUBLIC_KEY_PATH=/config/keys/public_key.pem
JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=30

# Database
DATABASE_URL=...
USE_CLOUD_STORAGE=true/false

# Email
SMTP_SERVER=...
SMTP_USERNAME=...
SMTP_PASSWORD=...
FROM_EMAIL=noreply@nuts.services

# Application
APP_DOMAIN=auth.nuts.services
BRAND_NAME=Gnosis Auth
```

### 6.2. Database Schema
```sql
-- Users table
CREATE TABLE users (
    email VARCHAR PRIMARY KEY,
    name VARCHAR,
    created TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- AHP Tokens table  
CREATE TABLE ahp_tokens (
    token_id VARCHAR PRIMARY KEY,
    user_email VARCHAR REFERENCES users(email),
    token_hash VARCHAR, -- Hashed token value
    name VARCHAR,
    scopes JSON,
    created TIMESTAMP,
    expires TIMESTAMP,
    last_used TIMESTAMP,
    active BOOLEAN DEFAULT true
);
```

### 6.3. API Response Formats
```json
// POST /auth response
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
    "token_type": "Bearer", 
    "expires_in": 1800,
    "scope": "read write gnosis-ahp:read gnosis-ocr:process"
}

// Error response
{
    "error": "invalid_token",
    "error_description": "The provided AHP token is invalid or expired"
}
```

This plan provides a complete roadmap for implementing the federated authentication system while maintaining the simplicity of the AHP protocol vision.