# Open WebUI (Oceancalm Fork)

Extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline. It supports various LLM runners like Ollama and OpenAI-compatible APIs, with a built-in inference engine for RAG.

## Project Overview

- **Frontend**: SvelteKit, TypeScript, Tailwind CSS v4, Vite.
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy/Peewee, SQLite/PostgreSQL.
- **Key Features**: RAG integration, Voice/Video calls, Image generation, Web search, Multi-model chat, RBAC, and Enterprise Auth (LDAP/SSO).
- **Architecture**: A SvelteKit frontend communicating with a FastAPI backend. The backend handles model orchestration, document processing for RAG, and user management.

## Project Structure

- `backend/`: Python backend source code.
    - `open_webui/`: Main package containing routers, models, and utilities.
    - `open_webui/main.py`: Entry point for the FastAPI application.
- `src/`: SvelteKit frontend source code.
    - `lib/components/`: Reusable UI components.
    - `routes/`: SvelteKit pages and layouts.
- `docs/`: Extensive documentation for users and developers.
- `static/`: Static assets (images, icons, etc.).
- `docker-compose.yaml`: Primary orchestration for containerized deployment.

## Building and Running

### Local Development

#### 1. Backend
```bash
cd backend
# Recommended: Create a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./dev.sh
```
The backend typically runs on `http://localhost:8080`.

#### 2. Frontend
```bash
# From the root directory
npm install
npm run dev
```
The frontend typically runs on `http://localhost:5173`.

### Docker Deployment
```bash
docker build -t open-webui .
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui open-webui
```

## Development Conventions

- **Backend Formatting**: Uses `black`. Run `npm run format:backend`.
- **Frontend Formatting**: Uses `prettier`. Run `npm run format`.
- **Linting**: Run `npm run lint` for a comprehensive check of both frontend and backend.
- **Testing**:
    - **Frontend**: `npm run test:frontend` (Vitest).
    - **E2E**: `npm run cy:open` (Cypress).
    - **Backend**: `pytest` in the `backend/` directory.
- **Internationalization**: Uses `i18next`. Language files are in `src/lib/i18n`. Run `npm run i18n:parse` to update keys.

## Key Files

- `package.json`: Frontend dependencies and build scripts.
- `pyproject.toml`: Backend dependencies and hatchling build configuration.
- `backend/open_webui/config.py`: Central configuration for backend features and environment variables.
- `backend/open_webui/main.py`: FastAPI app initialization and middleware setup.
- `src/lib/constants.ts`: Frontend-side constants and configuration.
