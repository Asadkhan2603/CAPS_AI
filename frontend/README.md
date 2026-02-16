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

## Using Auth and CRUD Pages

1. Open frontend at `http://localhost:5173`.
2. Register at `/register` or login at `/login`.
3. After login, token is stored automatically in browser local storage.
4. Navigate to `Courses`, `Years`, `Classes`, `Sections`, `Section Subjects`, `Students`, `Subjects`, `Assignments`, and `Submissions`.

## Scripts

- `npm run dev` Start development server
- `npm run build` Build production assets
- `npm run preview` Preview production build
