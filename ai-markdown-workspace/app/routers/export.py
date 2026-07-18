"""Placeholder - Export router"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/chat/markdown")
@router.get("/chat/json")
async def placeholder(request: Request):
    return HTMLResponse("<div class='p-4'>Export - Coming soon...</div>")
