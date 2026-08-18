# Hospital Management System (HMS)

Lightweight FastAPI + React hospital management system with an in-app, local Proof-of-Work blockchain used for encrypted audit anchoring and simulated payments. This repository contains a minimal backend API, a React/Vite frontend, a tiny PoW blockchain (no external APIs or wallets), and CI for the frontend.

**Quick links**
- Backend entry: `main.py`
- Blockchain implementation: `blockchain.py`
- Frontend: `frontend/` (Vite + React)

**Key features**
- JWT-only authentication and role-based scaffolding
- Patients, EHR (versioned), prescriptions, consent records
- Billing simulation and receipts (anchored to the in-app chain)
- In-app PoW blockchain with Fernet-encrypted transaction payloads
- Frontend SPA (React + Vite) with basic UI, form validation, toasts
- Frontend tests (Vitest) and GitHub Actions workflow to build-and-test

**Design note — Local-only blockchain**
- The chain is fully self-contained in `blockchain.py` with these properties:
  - Proof-of-Work (simple difficulty: leading hash nibbles) implemented locally.
  - Transactions may include sensitive `data` which is encrypted using `cryptography.fernet.Fernet`.
  - Fernet key is taken from the `BLOCKCHAIN_KEY` environment variable (base64). If not set, an ephemeral key is generated (development-only).
  - Anchors are simulated by writing an anchor record to `anchors.json` and also adding an on-chain transaction referencing that anchor id.
  - No external APIs, keys, or networks are used — everything is local and suitable for audit/demo purposes.

See `blockchain.py` for implementation details: `mine_block()`, `new_transaction()`, `new_block()`, `anchor_block()`, `get_anchors()`, `get_chain()`.

Security note: Fernet keys, JWT secrets, and production database credentials must be provisioned securely for any real deployment. The repository currently uses an ephemeral Fernet key by default which is NOT secure for production.

Getting started — backend

1. Create a virtual environment and install Python dependencies (example):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn sqlalchemy cryptography passlib[bcrypt] python-jose pydantic
```

2. Set environment variables (example `.env`):

```env
# Fernet key (base64) - optional but recommended for reproducible encrypted payloads
BLOCKCHAIN_KEY=Z3Vlc3N0ZXN0a2V5MTIzNDU2Nzg5MDEyMzQ1Ng==

# JWT / auth settings
SECRET_KEY=replace_this_with_a_secure_random_value
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# SQLALCHEMY DATABASE URL (example for SQLite file)
DATABASE_URL=sqlite:///./hms.db
```

3. Run the API server (development):

```bash
# from repository root
uvicorn main:app --reload --port 8000
```

The API is mounted under the `/api` prefix (e.g., `http://localhost:8000/api/`). Static assets will be served from `frontend/dist` if present.

Getting started — frontend

1. Install Node dependencies and run dev server:

```bash
cd frontend
npm install
npm run dev
```

2. Build the production bundle:

```bash
npm run build
```

Notes:
- The repository no longer tracks `frontend/dist`; the CI workflow builds in GitHub Actions. If you want the backend to serve a built frontend, run `npm run build` locally and ensure `frontend/dist` exists before starting the backend.

Tests and CI

- Frontend tests are implemented with Vitest. Run them locally:

```bash
cd frontend
npm test
```

- A GitHub Actions workflow (`.github/workflows/frontend-ci.yml`) runs the frontend tests and build on push/PR to `main`.

Development and debugging tips

- The Fernet key used by the blockchain controls encryption. To inspect encrypted payloads, pass the same `BLOCKCHAIN_KEY` value used by the server into a small Python snippet and call `blockchain.decrypt_data(token)`.
- Anchors are written to `anchors.json` in the working directory; they identify block index, block hash, and an `anchor_id` (SHA256-based). Anchoring is entirely local.
- For tests, the project uses in-memory SQLite patterns in test fixtures (see `tests/`) to avoid touching a production DB.

Future work and Phase 6

- Security hardening: rotate Fernet keys, secure JWT secret management, use HTTPS, CORS hardening
- Production containers: multi-stage Dockerfile and deploy playbooks
- CI: extend to run backend tests and build Docker images

License & contributions

This project is provided as-is for learning and prototyping. Contributions welcome — open a PR with a clear description.
# Hospital Management System (HMS) — upgraded with simple blockchain and UI

This repository contains a FastAPI-based Hospital Management System. I added a lightweight proof-of-work blockchain module and a small static UI to interact with it.

Quick start

1. Create a Python environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure your database by setting the `DATABASE_URL` environment variable (defaults to a local Postgres URL in `database.py`).

3. Run the app:

```bash
uvicorn main:app --reload
```

4. Open the UI at http://localhost:8000/ to view the simple dashboard.

Notes
- The API is namespaced under `/api` — e.g. `/api/blockchain/chain`.
- A lightweight blockchain is implemented in `blockchain.py` and is used to record EHR creation as transactions.
- This is a demo-grade blockchain for audit/logging and should not be used as a secure ledger in production.

Encryption & simulated payments

- Transaction payloads are encrypted using Fernet (`cryptography`) with a key from the `BLOCKCHAIN_KEY` environment variable. If unset, an ephemeral key is used (not safe for production).
- Transactions can represent payments by including `{"type":"payment","billing_id": <id>}` in the transaction `data`. When such transactions are submitted through the API, the server will mark the corresponding `Billing` record as `paid` (demo simulation).

Next steps you might ask me to do:
- Improve the UI with React or Svelte and authentication flows.
- Persist the blockchain to disk or integrate with a production ledger.
- Add automated tests and CI.

Frontend (React) scaffold

I added a minimal React + Vite frontend in the `frontend/` folder. To run it:

```bash
cd frontend
npm install
npm run dev
```

The React dev server runs on port 5173 by default and the backend allows CORS from localhost for development.
