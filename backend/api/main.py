"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import optimize_router, router as calculate_router

app = FastAPI(
    title="Mechora API",
    version="0.1.0",
    description="SaaS de calcul mécanique — module : poutres en flexion (RDM).",
)

# Vite dev server runs on :5173 by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(calculate_router)
app.include_router(optimize_router)
