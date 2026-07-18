"""Placeholder - Builders router"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

@router.get("/")
@router.get("/search")
async def placeholder(request: Request):
    return JSONResponse([])
