# Registry UI

Simple UI to browse OCI registry repositories using the `list_repositories()` method.

## Structure

```
src/ui/
├── server.py          # FastAPI backend (port 8080)
└── frontend/          # React + Vite + shadcn/ui
    ├── src/
    │   ├── components/ui/  # shadcn components
    │   ├── App.tsx         # Main UI component
    │   └── ...
    └── ...
```

## Run

**Terminal 1 - Backend:**
```bash
cd /home/cip/src/pallet
uv run python src/ui/server.py
```

**Terminal 2 - Frontend:**
```bash
cd src/ui/frontend
npm run dev
```

**Access:** http://localhost:5173

## Requirements

- Registry running at `localhost:5000`
- Backend API at `localhost:8080`
- Frontend at `localhost:5173`

## Features

- Lists all repositories from OCI registry
- Auto-refresh on load
- Manual refresh button
- Loading states
- Error handling
- shadcn/ui Card components
