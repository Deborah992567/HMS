from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from routers import router
from database import Base, engine

# Create the app and register API routes before mounting static files
app = FastAPI(title="Hospital Management System")

@app.on_event("startup")
def create_database_tables():
    """Make the demo usable on a fresh local install.

    Production deployments can still point DATABASE_URL at their managed database
    and replace this with migrations when they are introduced.
    """
    Base.metadata.create_all(bind=engine)

# Namespace API under /api so static files don't conflict with API routes
app.include_router(router, prefix="/api")

# Serve built frontend if present (frontend/dist), otherwise fall back to legacy `static/`
frontend_dist = "frontend/dist"
if os.path.exists(frontend_dist):
	app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
	app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Allow CORS for frontend development (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
