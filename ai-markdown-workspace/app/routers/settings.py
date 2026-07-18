"""Settings router with all configuration sections - Phase 4"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.services.timezone_service import format_wib, utc_now

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/")
async def settings_page(request: Request, db: Session = Depends(get_db)):
    """Render settings page with all sections"""
    from app.main import templates
    
    # Load all settings
    settings_rows = db.execute("SELECT * FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in settings_rows}
    
    # Get workspaces for RAG section
    workspaces = db.execute("SELECT * FROM workspaces").fetchall()
    
    return templates.TemplateResponse("pages/settings.html", {
        "request": request,
        "settings": settings,
        "workspaces": workspaces,
        "wib_now": format_wib(utc_now())
    })


@router.post("/ai")
async def save_ai_settings(
    request: Request,
    api_endpoint: str = Form(...),
    api_key: str = Form(""),
    default_model: str = Form("mimo-v2.5"),
    temperature: float = Form(0.7),
    max_tokens: int = Form(4096),
    thinking_mode: str = Form("off"),
    language: str = Form("en"),
    use_xiaomi_mimo: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Save AI settings including Xiaomi Mimo Plan support"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "ai_api_endpoint": api_endpoint,
        "ai_api_key": api_key,
        "ai_default_model": default_model,
        "ai_temperature": str(temperature),
        "ai_max_tokens": str(max_tokens),
        "ai_thinking_mode": thinking_mode,
        "ai_language": language,
        "use_xiaomi_mimo": "true" if use_xiaomi_mimo else "false"
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ AI settings saved
        </div>
    """)


@router.post("/markdown")
async def save_markdown_settings(
    request: Request,
    markdown_theme: str = Form("github-dark"),
    syntax_highlight: bool = Form(False),
    code_block_copy: bool = Form(False),
    mathjax_enabled: bool = Form(False),
    mermaid_enabled: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Save Markdown rendering settings"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "markdown_theme": markdown_theme,
        "syntax_highlight": "true" if syntax_highlight else "false",
        "code_block_copy": "true" if code_block_copy else "false",
        "mathjax_enabled": "true" if mathjax_enabled else "false",
        "mermaid_enabled": "true" if mermaid_enabled else "false"
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ Markdown settings saved
        </div>
    """)


@router.post("/export")
async def save_export_settings(
    request: Request,
    export_format: str = Form("markdown"),
    include_timestamps: bool = Form(False),
    include_metadata: bool = Form(False),
    timestamp_format: str = Form("wib"),
    db: Session = Depends(get_db)
):
    """Save Export settings"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "export_format": export_format,
        "include_timestamps": "true" if include_timestamps else "false",
        "include_metadata": "true" if include_metadata else "false",
        "timestamp_format": timestamp_format
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ Export settings saved
        </div>
    """)


@router.post("/rag")
async def save_rag_settings(
    request: Request,
    rag_enabled: bool = Form(False),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    embedding_model: str = Form("all-MiniLM-L6-v2"),
    similarity_threshold: float = Form(0.7),
    db: Session = Depends(get_db)
):
    """Save RAG settings"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "rag_enabled": "true" if rag_enabled else "false",
        "chunk_size": str(chunk_size),
        "chunk_overlap": str(chunk_overlap),
        "embedding_model": embedding_model,
        "similarity_threshold": str(similarity_threshold)
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ RAG settings saved
        </div>
    """)


@router.post("/token")
async def save_token_settings(
    request: Request,
    track_usage: bool = Form(False),
    cost_per_1k_prompt: float = Form(0.0),
    cost_per_1k_completion: float = Form(0.0),
    budget_limit: float = Form(0.0),
    db: Session = Depends(get_db)
):
    """Save Token usage settings"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "track_usage": "true" if track_usage else "false",
        "cost_per_1k_prompt": str(cost_per_1k_prompt),
        "cost_per_1k_completion": str(cost_per_1k_completion),
        "budget_limit": str(budget_limit)
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ Token settings saved
        </div>
    """)


@router.post("/toolcall")
async def save_toolcall_settings(
    request: Request,
    tool_call_enabled: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Save Tool Call settings (OFF by default)"""
    now = utc_now().isoformat()
    
    db.execute("""
        INSERT INTO settings (key, value, updated_at) 
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
    """, ("tool_call_enabled", "true" if tool_call_enabled else "false", now, "true" if tool_call_enabled else "false", now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ Tool Call settings saved
        </div>
    """)


@router.post("/mcp")
async def save_mcp_settings(
    request: Request,
    mcp_enabled: bool = Form(False),
    mcp_servers: str = Form(""),
    db: Session = Depends(get_db)
):
    """Save MCP settings (OFF by default)"""
    now = utc_now().isoformat()
    
    db.execute("""
        INSERT INTO settings (key, value, updated_at) 
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
    """, ("mcp_enabled", "true" if mcp_enabled else "false", now, "true" if mcp_enabled else "false", now))
    
    db.execute("""
        INSERT INTO settings (key, value, updated_at) 
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
    """, ("mcp_servers", mcp_servers, now, mcp_servers, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ MCP settings saved
        </div>
    """)


@router.post("/theme")
async def save_theme_settings(
    request: Request,
    theme: str = Form("dark"),
    font_size: str = Form("base"),
    db: Session = Depends(get_db)
):
    """Save UI theme settings"""
    now = utc_now().isoformat()
    
    settings_to_save = {
        "ui_theme": theme,
        "ui_font_size": font_size
    }
    
    for key, value in settings_to_save.items():
        db.execute("""
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?
        """, (key, value, now, value, now))
    
    db.commit()
    
    return HTMLResponse("""
        <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
             x-data="{ show: true }" x-show="show"
             x-init="setTimeout(() => show = false, 3000)">
            ✓ Theme settings saved
        </div>
    """)
