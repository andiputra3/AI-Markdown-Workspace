"""Placeholder - RAG router"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/")
async def placeholder(request: Request):
    return HTMLResponse("<div class='p-4'>RAG - Coming soon...</div>")
