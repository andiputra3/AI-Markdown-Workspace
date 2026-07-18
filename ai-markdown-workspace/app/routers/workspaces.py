"""Placeholder - Workspaces router"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/")
@router.get("/switch/{workspace_id}")
@router.post("/create")
async def placeholder(request: Request):
    return HTMLResponse("<div class='p-4'>Workspaces - Coming soon...</div>")
