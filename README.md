# Gnosis Auth Service

Gnosis Auth is a centralized authentication and authorization microservice built with FastAPI. It is designed to handle user management, OAuth 2.0 flows, API token issuance, and session management for the Gnosis ecosystem.

## Features

-   **User Authentication:** Standard email/password login and registration.
-   **OAuth 2.0 Provider:** Acts as an OAuth 2.0 provider for other Gnosis services.
-   **API Token Management:** Create, view, and revoke API tokens for programmatic access.
-   **Session Management:** Securely manages user sessions.
-   **Containerized:** Ready to run with Docker and Docker Compose.
-   **Google Cloud NDB:** Uses Google Cloud NDB for data storage, with a local emulator for development.

## Getting Started

### Prerequisites

-   Python 3.11+
-   Docker and Docker Compose
-   An active `gcloud` session (for emulator)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:kordless/gnosis-auth.git
    cd gnosis-auth
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Copy the example environment file and fill in the required values.
    ```bash
    cp .env.example .env
    ```
    *Note: You will need to generate OAuth credentials from the Google Cloud Console and place them in `client_secret.json`.*

### Running the Application

#### With Docker (Recommended for Development)

The simplest way to get the service and its database emulator running is with Docker Compose:

```bash
docker-compose up --build
```

The service will be available at `http://localhost:5000`.

#### Locally

To run the application directly on your host machine:

1.  **Start the NDB emulator:**
    ```bash
    gcloud beta emulators datastore start --project=gnosis-auth-dev --host-port=0.0.0.0:8089 --no-store-on-disk
    ```

2.  **Run the FastAPI server:**
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 5000 --reload
    ```

## Project Structure

-   `app.py`: The main FastAPI application entry point.
-   `core/`: Core application logic, including configuration, schemas, and storage services.
-   `web/`: Contains the web-facing parts of the application.
    -   `routes/`: API route definitions.
    -   `templates/`: Jinja2 HTML templates.
    -   `static/`: Static assets (CSS, JS, images).
-   `storage/`: Local directory for persistent data (ignored by git).
-   `scripts/`: Utility and deployment scripts.
-   `Dockerfile`: Instructions for building the production Docker image.
-   `docker-compose.yml`: Defines the development environment services.
-   `requirements.txt`: Python package dependencies.