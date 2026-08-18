# HMS Architecture

This document describes the high-level architecture of the Hospital Management System (HMS), dataflows, and deployment notes.

## Overview

- Backend: FastAPI (Python) with SQLAlchemy persistence (SQLite/Postgres), JWT auth, and an in-app PoW blockchain for anchoring payment/receipt transactions.
- Frontend: React + Vite SPA, styled with Tailwind CSS. Tests with Vitest and @testing-library/react.
- CI: GitHub Actions builds frontend and runs tests; recommended backend CI to run Python tests and linting.

## Components

- `main.py` — FastAPI app entry; mounts `/api` and optionally serves `frontend/dist` for production.
- `routers.py` — API route definitions (patients, EHR, prescriptions, consents, payments, receipts, blockchain).
- `database.py`, `models.py`, `schemas.py` — DB setup, SQLAlchemy models, Pydantic schemas.
- `utils.py` — auth helpers (JWT), password hashing, role checks.
- `blockchain.py` — in-app PoW blockchain. Transactions are encrypted using Fernet; anchors persisted to `anchors.json`.
- `frontend/` — React app components, pages, Tailwind config, tests.

## Dataflow (EHR → Anchor Example)

1. User creates an EHR record via `POST /api/ehr/`.
2. Backend validates and stores the EHR in the database.
3. A transaction payload (receipt/payment metadata) is created and encrypted with `Fernet`.
4. The encrypted payload is added to the in-app blockchain as a transaction and mined (`proof_of_work`).
5. A block anchor record (block index / hash) is stored in `anchors.json` and optionally returned to the client as `anchor_id` on receipts.

## Auth

- Authentication: JWT access tokens issued at `/api/token` (username/password). Frontend stores token in `localStorage` and sends `Authorization: Bearer <token>` for protected endpoints.
- Authorization: RBAC utilities in `utils.py` provide `require_roles` checks per-route.

## Mermaid Diagram

```mermaid
graph LR
  subgraph Frontend
    A[React SPA]
  end
  subgraph Backend
    B[FastAPI /api]
    DB[(SQL DB)]
    BC[In-app Blockchain]
    FS[anchors.json]
  end
  A -->|HTTP (JWT)| B
  B --> DB
  B --> BC
  BC --> FS
  B -->|reads/writes| FS
```

## Deployment & CI notes

- Frontend built with `npm run build` (Vite), artifacts served by the backend from `frontend/dist` or deployed separately to a static host.
- Do not commit `frontend/dist` to the repo; CI should build artifacts.
- Add GitHub Actions workflow to run backend tests, linting, and (optionally) build and deploy the frontend.

## Security considerations

- Keep `BLOCKCHAIN_KEY` (Fernet) secret in environment variables. If absent, the app will use an ephemeral key (development only).
- JWT secret must be rotated and protected.
- For production, enable HTTPS, secure cookie usage (if switching away from localStorage), and harden database access.

## Next steps

- Add sequence diagrams for payment lifecycle (optional).
- Add architecture diagram images to `docs/` if you want PNG/SVG exports of the Mermaid diagrams.
