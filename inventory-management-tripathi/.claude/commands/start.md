---
description: Start the frontend and backend servers
---

Kill any existing servers on ports 3000 and 8001, then start both the backend (FastAPI on port 8001) and frontend (Vite on port 3000) development servers in the background.

**Backend:** `cd server && uv run python main.py`
**Frontend:** `cd client && npm run dev`

To kill existing processes on a port:
- macOS/Linux: `lsof -ti:3000,8001 | xargs kill -9 2>/dev/null || true`
- Windows: Use `netstat -aon | findstr :PORT` to find PIDs, then `taskkill /F /PID <pid>`

After starting, verify:
- Backend: http://localhost:8001/docs
- Frontend: http://localhost:3000
