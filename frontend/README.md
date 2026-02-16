# Frontend

React + Vite frontend scaffold for CAPS AI.

## Setup

```bash
npm install
copy .env.example .env
npm run dev
```

## Environment

- `VITE_API_BASE_URL` (default: `http://localhost:8000/api/v1`)

## Using Protected CRUD Pages

1. Login via backend API (`POST /api/v1/auth/login`) in Swagger or Postman.
2. Copy `access_token` from response.
3. Open Dashboard and paste token into the `Auth Token` box.
4. Navigate to `Students`, `Subjects`, or `Assignments`.

## Scripts

- `npm run dev` Start development server
- `npm run build` Build production assets
- `npm run preview` Preview production build
