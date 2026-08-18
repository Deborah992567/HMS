from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import router
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Management System")

# Serve the single-page UI from the static folder at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Namespace API under /api so static files don't conflict with API routes
app.include_router(router, prefix="/api")
