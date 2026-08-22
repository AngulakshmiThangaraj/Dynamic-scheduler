import sys
import os

# Add root directory to python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database.schema import init_db, SessionLocal, User
from backend.database.seed import seed_database
from backend.routes import (
    auth, users, events, schedule, conflicts, rooms_resources, availability, analytics, notifications, history_audit
)

app = FastAPI(
    title="Dynamic Event Scheduling API",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler returning clean JSON
@app.exception_handler(Exception)
async def vercel_global_exception_handler(request: Request, exc: Exception):
    print(f"Vercel Serverless Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": str(exc),
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc)
            }
        }
    )

# Safe DB Initialization Middleware
_db_seeded = False

@app.middleware("http")
async def ensure_db_middleware(request: Request, call_next):
    global _db_seeded
    if not _db_seeded:
        try:
            init_db()
            db = SessionLocal()
            try:
                if not db.query(User).first():
                    seed_database()
            finally:
                db.close()
            _db_seeded = True
        except Exception as e:
            print(f"DB Middleware Init Warning: {e}")

    response = await call_next(request)
    return response

# Include Routers with /api prefix
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(schedule.router)
app.include_router(conflicts.router)
app.include_router(rooms_resources.router)
app.include_router(availability.router)
app.include_router(analytics.router)
app.include_router(notifications.router)
app.include_router(history_audit.router)

# Healthcheck endpoint
@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "message": "Dynamic Event Scheduling API is live"}
