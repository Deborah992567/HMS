from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from routers import router
from database import Base, engine, SessionLocal
from sqlalchemy import inspect, text
from models import Doctor, Service

# Create the app and register API routes before mounting static files
app = FastAPI(title="Hospital Management System")

@app.on_event("startup")
def create_database_tables():
    """Make the demo usable on a fresh local install.

    Production deployments can still point DATABASE_URL at their managed database
    and replace this with migrations when they are introduced.
    """
    Base.metadata.create_all(bind=engine)
    # Keep local/demo databases created before the patient portal compatible.
    # SQLAlchemy's create_all creates missing tables but intentionally never
    # changes existing ones, so add these non-destructive nullable columns.
    inspector = inspect(engine)
    upgrades = {
        "patients": {"hashed_password": "VARCHAR"},
        "appointments": {"service_id": "INTEGER"},
        "billing": {"appointment_id": "INTEGER", "description": "VARCHAR"},
    }
    with engine.begin() as connection:
        for table, columns in upgrades.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
    # First-run demo directory: ten clearly simulated doctors per service.
    # Administrators can replace these records with their real clinicians.
    if os.getenv("HMS_SEED_DEMO_DATA", "true").lower() == "true":
        service_names = [
            "General Consultation", "Emergency Care", "Cardiology", "Dermatology",
            "Dentistry", "ENT", "Family Medicine", "Gastroenterology", "Neurology",
            "Obstetrics & Gynaecology", "Ophthalmology", "Orthopaedics", "Paediatrics",
            "Physiotherapy", "Psychiatry", "Pulmonology", "Radiology", "Surgery",
            "Urology", "Vaccination & Immunisation",
        ]
        db = SessionLocal()
        try:
            if not db.query(Service).first():
                db.add_all([Service(name=name, description=f"{name} service", duration_minutes=30) for name in service_names])
                clinician_names = ["Avery", "Blake", "Cameron", "Drew", "Ellis", "Finley", "Gray", "Harper", "Indigo", "Jordan"]
                db.add_all([Doctor(name=f"Dr. {name} {index + 1} (Demo)", specialty=service)
                            for service in service_names for index, name in enumerate(clinician_names)])
                db.commit()
        finally:
            db.close()

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
