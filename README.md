# mangedong

A minimal full-stack task board used to demonstrate a working Cloud Agent
development environment. The backend is an [Express](https://expressjs.com/)
JSON API; the frontend is a dependency-free static UI served by the same
server. Tasks are kept in an in-memory store.

## Requirements

- Node.js >= 20 (developed against Node 22)

## Getting started

```bash
npm install        # install dependencies
npm run dev        # start the dev server with auto-reload on http://localhost:3000
```

Then open http://localhost:3000 to use the task board.

## Scripts

| Command | Description |
| --- | --- |
| `npm start` | Start the production server (`src/server.js`). |
| `npm run dev` | Start the server with `node --watch` auto-reload. |
| `npm test` | Run the API test suite with the built-in Node test runner. |
| `npm run lint` | Lint the project with ESLint. |
| `npm run build` | Produce a deployable `dist/` bundle. |

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Health check. |
| `GET` | `/api/tasks` | List all tasks. |
| `POST` | `/api/tasks` | Create a task (`{ "title": "..." }`). |
| `PATCH` | `/api/tasks/:id` | Update a task (`title` and/or `done`). |
| `DELETE` | `/api/tasks/:id` | Delete a task. |

## Configuration

- `PORT` – HTTP port (default `3000`).
- `HOST` – bind address (default `0.0.0.0`).
