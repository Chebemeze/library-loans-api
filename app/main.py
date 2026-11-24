"""Maple Street Library: HTTP composition root."""

from fastapi import FastAPI

from app.routers import books, copies, fines, health, loans, members
from app.routers.errors import register_error_handlers

app = FastAPI(title="Maple Street Library Loans API", version="1.0.0")
register_error_handlers(app)
for router in (books.router, copies.router, members.router, loans.router, fines.router):
    app.include_router(router, prefix="/v1")
app.include_router(health.router)
