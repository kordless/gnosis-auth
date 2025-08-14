# Organization Notes

This file documents thoughts on organizing the gnosis project structure for better maintainability.

## Current State Analysis

The gnosis-auth service is a FastAPI application that implements email-based "magic link" authentication. It follows a clean architecture with:

1. **Core** - Contains models, configuration, and utility functions
2. **Web** - Contains routes and templates for the web interface
3. **Templates** - HTML templates for the authentication flow

## Key Features

- Email-based authentication with magic links
- JWT token generation and verification
- OAuth integration (Google, GitHub)
- Development mode with console token output
- JWKS endpoint for token verification

## Directory Structure Observations

The current structure is well-organized with a clear separation of concerns:
- `core/` contains business logic and data models
- `web/routes/` contains API endpoints
- `web/templates/` contains HTML templates

## Relationship to Other Services

This service integrates with:
- gnosis-web (dashboard that consumes auth tokens)
- gnosis-wraith (web crawler)
- gnosis-ahp (agent host protocol)
- gnosis-ocr (optional OCR service)

All services are orchestrated through docker-compose files in the gnosis-web directory.

## Proposed Better Organization

See discussion in the main gnosis directory GEMINI.md file for ideas on reorganizing the entire project structure to better group related components and centralize orchestration.