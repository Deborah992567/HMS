# API Reference

Base path: `/api`

Authentication: JWT Bearer token obtained from `POST /api/token`.

Notes: All protected routes require `Authorization: Bearer <token>` header.

## Endpoints

- `POST /api/token` — Obtain JWT
  - Auth: Public
  - Request (form): `username`, `password`
  - Response: `{ "access_token": "...", "token_type": "bearer" }`

- `GET /api/patients/` — List patients
  - Auth: Bearer
  - Response: `[ { "id": 1, "name": "Alice" }, ... ]`

- `POST /api/patients/` — Create patient
  - Auth: Bearer
  - Request JSON: `{ "name": "Alice", "dob": "1990-01-01" }`
  - Response: patient object

- `GET /api/patients/{patient_id}/ehr` — List EHR versions for a patient
  - Auth: Bearer + consent enforced
  - Response: `[ { "id": 1, "patient_id": 1, "diagnosis": "...", "created_at": "..." }, ... ]`

- `POST /api/ehr/` — Create new EHR record
  - Auth: Bearer
  - Request JSON: `{ "patient_id": 1, "diagnosis": "...", "medication": "...", "notes": "..." }`
  - Response: EHR object

- `POST /api/prescriptions/` — Create prescription
  - Auth: Bearer
  - Request JSON: `{ "patient_id": 1, "doctor_id": 2, "medication": "Drug", "dosage": "1x/day" }`

- `POST /api/consents/` — Grant consent
  - Auth: Bearer
  - Request JSON: `{ "patient_id": 1, "granted_to": "provider:2", "scope": "ehr.read" }`

- `POST /api/payments/simulate` — Simulate a payment and anchor to chain
  - Auth: Bearer
  - Request JSON: `{ "billing_id": 123 }`
  - Response: `{ "message": "Payment simulated", "anchor": { "block_index": 5, "block_hash": "..." } }`

- `POST /api/receipts/` — Create a receipt (stored and optionally anchored)
  - Auth: Bearer
  - Request JSON: `{ "billing_id": 123, "amount": 199.99 }`
  - Response: `{ "id": 1, "billing_id": 123, "amount": 199.99, "anchor_id": "block:5" }`

- `GET /api/receipts/` — List receipts
  - Auth: Bearer
  - Response: `[ { "id": 1, "billing_id": 123, "amount": 199.99, "anchor_id": "block:5" }, ... ]`

- `GET /api/blockchain/chain` — Get full chain
  - Auth: Public
  - Response: `{ "length": N, "chain": [ ...blocks... ] }`

- `POST /api/blockchain/anchor` — Force anchor of pending transactions
  - Auth: Bearer (admin)
  - Response: `{ "message": "anchored", "block_index": 6 }`

- `GET /api/blockchain/block/{index}` — Get block by index
  - Auth: Public
  - Response: block object with `index`, `previous_hash`, `nonce`, `transactions`, `timestamp`, `hash`

## Schemas (examples)

- Receipt

```
{
  "id": 1,
  "billing_id": 123,
  "amount": 199.99,
  "anchor_id": "block:5"
}
```

- EHR

```
{
  "id": 1,
  "patient_id": 1,
  "diagnosis": "Hypertension",
  "medication": "Lisinopril",
  "notes": "Follow up in 2 weeks",
  "created_at": "2026-08-18T12:00:00Z"
}
```

## Error responses

- Standard JSON error: `{ "detail": "message" }` with appropriate status codes (400, 401, 403, 404, 500).

## Usage examples (curl)

Get chain (public):

```bash
curl -s https://your-host/api/blockchain/chain
```

Create receipt (authenticated):

```bash
curl -X POST https://your-host/api/receipts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"billing_id":123, "amount":99.95}'
```
