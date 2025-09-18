from fastapi import FastAPI
from routers import router
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Management System")
app.include_router(router)
