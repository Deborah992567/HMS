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
