from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router

app = FastAPI(title="Freelance Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(router)
