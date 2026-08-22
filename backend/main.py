import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.database.schema import init_db
from backend.database.seed import seed_database
from backend.routes import (
    auth, users, events, schedule, conflicts, rooms_resources, availability, analytics, notifications, history_audit
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup database initialization and seeding
    init_db()
    seed_database()
    yield

app = FastAPI(
    title="Dynamic Event Scheduling & Conflict Resolver API",
    version="1.0.0",
    description="Enterprise production REST API for scheduling optimization, multi-dimensional conflict detection, what-if simulations, and automated resolution.",
    lifespan=lifespan
)

# CORS Configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Error Handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": []
            }
        }
    )

# Include Routers
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

# Mount Frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=5000, reload=True)
