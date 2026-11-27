# frontend/ — BoneAge AI frontend

React + TypeScript + Vite + Tailwind frontend, translating every screen in [`design/`](../design/README.md) pixel-for-pixel — see [docs/design.md](../docs/design.md) and the lock note in [CLAUDE.md](../CLAUDE.md#frontend-design-locked). Talks to the FastAPI backend in [`backend/`](../backend/README.md).

## Setup

```bash
cd frontend
npm install
npm run dev
```

Dev server runs at `http://localhost:5173`. API calls to `/api/*` are proxied to `http://127.0.0.1:8000` (the backend, see `vite.config.ts`) — no CORS setup needed locally, and no `VITE_API_BASE_URL` needed either (see below). Start the backend separately per [backend/README.md](../backend/README.md).

## Scripts

```bash
npm run dev       # dev server with HMR
npm run build     # tsc -b && vite build -> dist/
npm run preview   # preview the production build locally
npm run test       # vitest run
npm run test:watch # vitest, watch mode
npm run lint       # oxlint
```

## Configuration

- `VITE_API_BASE_URL` — base URL the API client (`src/api/client.ts`) talks to. Unset locally (defaults to `/api`, handled by the Vite proxy above). In production (Vercel), set it as a Production environment variable on the Vercel project so it's baked in at build time — see [README.md#deployment-setup-vercel--render--github-actions](../README.md#deployment-setup-vercel--render--github-actions).
- `vercel.json` — SPA rewrite so client-side routes (`react-router-dom`'s `BrowserRouter`) survive a deep link or page refresh on Vercel.

## Tests

`npm run test` runs Vitest + Testing Library (jsdom environment, see `vite.config.ts`) — component tests plus an integration test of the sign-in → upload → predict → agent-review flow against a mocked API client (`src/test/`). No backend or network access needed.
