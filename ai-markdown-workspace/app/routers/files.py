"""File management router with full audit logging - Phase 3"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
from pathlib import Path

from app.database import get_db
from app.services.file_manager import get_file_manager, FileManager
from app.services.audit_log import AuditLogService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/")
async def file_manager_page(request: Request, db: Session = Depends(get_db)):
    """Render file manager page"""
    from app.main import templates
    
    # Get current workspace (default to first)
    workspace = db.execute(
        "SELECT * FROM workspaces LIMIT 1"
    ).fetchone()
    
    if not workspace:
        return HTMLResponse("<div class='p-4'>No workspace found. Create one first.</div>")
    
    # List files in workspace using FileManager
    fm = get_file_manager()
    files = await fm.list_files(
        workspace_id=workspace["id"],
        workspace_name=workspace["name"]
    )
    
    return templates.TemplateResponse("pages/file_manager.html", {
        "request": request,
        "workspace": workspace,
        "files": sorted(files, key=lambda x: (not x.get("is_directory", False), x["name"]))
    })


@router.post("/generate")
async def generate_file(
    request: Request,
    message_id: int = Form(...),
    block_index: int = Form(...),
    db: Session = Depends(get_db)
):
    """Generate file from code block in AI response"""
    fm = get_file_manager()
    
    # Get message and extract code block
    msg = db.execute(
        "SELECT * FROM messages WHERE id = ?", (message_id,)
    ).fetchone()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Parse code blocks from raw_content
    import re
    code_blocks = re.findall(r'```(\w+)?\n(.*?)```', msg["raw_content"] or msg["content"], re.DOTALL)
    
    if block_index >= len(code_blocks):
        return HTMLResponse("""
            <div class="bg-red-600 text-white px-4 py-2 rounded shadow"
                 x-data="{ show: true }" x-show="show"
                 x-init="setTimeout(() => show = false, 3000)">
                ✗ Code block not found
            </div>
        """)
    
    language, code = code_blocks[block_index]
    
    # Get workspace
    workspace = db.execute(
        "SELECT * FROM workspaces WHERE id = ?", (msg["session_id"],)
    ).fetchone()
    
    if not workspace:
        # Try to get workspace from session
        session = db.execute(
            "SELECT workspace_id FROM chat_sessions WHERE id = ?", (msg["session_id"],)
        ).fetchone()
        if session:
            workspace = db.execute(
                "SELECT * FROM workspaces WHERE id = ?", (session["workspace_id"],)
            ).fetchone()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Determine filename extension
    ext_map = {"python": "py", "javascript": "js", "typescript": "ts", "html": "html", "css": "css", "markdown": "md", "sql": "sql", "json": "json", "yaml": "yaml", "yml": "yaml", "xml": "xml", "txt": "txt"}
    ext = ext_map.get(language.lower() if language else "", "txt")
    
    # Generate filename
    filename = f"generated_{block_index}.{ext}"
    
    try:
        # Create file with audit logging
        result = await fm.create_file(
            workspace_id=workspace["id"],
            workspace_name=workspace["name"],
            file_path=filename,
            content=code,
            source_type="chat_message",
            source_id=message_id,
            source_description=f"Generated from message {message_id}, block {block_index}",
        )
        
        return HTMLResponse(f"""
            <div class="bg-green-600 text-white px-4 py-2 rounded shadow"
                 x-data="{{ show: true }}" x-show="show"
                 x-init="setTimeout(() => show = false, 3000)">
                ✓ Generated {filename}
            </div>
            <script>
                // Refresh file tree
                htmx.trigger('#file-tree', 'refreshFiles');
            </script>
        """)
    except Exception as e:
        return HTMLResponse(f"""
            <div class="bg-red-600 text-white px-4 py-2 rounded shadow"
                 x-data="{{ show: true }}" x-show="show"
                 x-init="setTimeout(() => show = false, 3000)">
                ✗ Error: {str(e)}
            </div>
        """)


@router.post("/create")
async def create_file(
    request: Request,
    path: str = Form(...),
    content: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create new file"""
    fm = get_file_manager()
    
    workspace = db.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    try:
        await fm.create_file(
            workspace_id=workspace["id"],
            workspace_name=workspace["name"],
            file_path=path,
            content=content,
            source_type="manual",
            source_description="Created via file manager"
        )
        
        return HTMLResponse("""
            <div class="bg-green-600 text-white px-4 py-2 rounded">✓ File created</div>
            <script>htmx.trigger('#file-tree', 'refreshFiles');</script>
        """)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{file_path:path}/edit")
async def edit_file(
    request: Request,
    file_path: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    """Edit existing file"""
    fm = get_file_manager()
    
    workspace = db.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    try:
        await fm.edit_file(
            workspace_id=workspace["id"],
            workspace_name=workspace["name"],
            file_path=file_path,
            new_content=content,
            source_type="manual",
            source_description="Edited via file manager"
        )
        
        return HTMLResponse("""
            <div class="bg-green-600 text-white px-4 py-2 rounded">✓ File saved</div>
        """)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{file_path:path}")
async def delete_file(
    request: Request,
    file_path: str,
    db: Session = Depends(get_db)
):
    """Delete file"""
    fm = get_file_manager()
    
    workspace = db.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    try:
        await fm.delete_file(
            workspace_id=workspace["id"],
            workspace_name=workspace["name"],
            file_path=file_path,
            source_type="manual",
            source_description="Deleted via file manager"
        )
        
        return HTMLResponse("""
            <div class="bg-green-600 text-white px-4 py-2 rounded">✓ File deleted</div>
            <script>htmx.trigger('#file-tree', 'refreshFiles');</script>
        """)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{file_path:path}/rename")
async def rename_file(
    request: Request,
    file_path: str,
    new_path: str = Form(...),
    db: Session = Depends(get_db)
):
    """Rename/move file"""
    fm = get_file_manager()
    
    workspace = db.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    try:
        await fm.rename_file(
            workspace_id=workspace["id"],
            workspace_name=workspace["name"],
            old_path=file_path,
            new_path=new_path,
            source_type="manual",
            source_description=f"Renamed from {file_path} to {new_path}"
        )
        
        return HTMLResponse("""
            <div class="bg-green-600 text-white px-4 py-2 rounded">✓ File renamed</div>
            <script>htmx.trigger('#file-tree', 'refreshFiles');</script>
        """)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{file_path:path}/history")
async def get_file_history(
    request: Request,
    file_path: str,
    db: Session = Depends(get_db)
):
    """Get file creation history"""
    audit = AuditLogService()
    
    workspace = db.execute("SELECT * FROM workspaces LIMIT 1").fetchone()
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    history = audit.get_file_history(workspace["id"], file_path)
    
    from app.main import templates
    return templates.TemplateResponse("partials/file_history.html", {
        "request": request,
        "history": history,
        "file_path": file_path
    })
