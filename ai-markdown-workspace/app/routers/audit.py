"""Audit Log Router for File Creation Log."""
import json
from typing import Optional
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment

from app.database import get_sync_connection
from app.services.audit_log import AuditLogService
from app.services.timezone_service import from_iso_utc, format_wib

router = APIRouter()


def get_audit_service() -> AuditLogService:
    """Dependency to get audit log service."""
    return AuditLogService()


@router.get("/", response_class=HTMLResponse)
async def audit_dashboard(request: Request):
    """Render audit dashboard page."""
    db = get_sync_connection()
    
    # Get all workspaces
    workspaces = db.execute(
        "SELECT id, name FROM workspaces ORDER BY name"
    ).fetchall()
    
    # Get current workspace (default to first)
    current_workspace = None
    if workspaces:
        current_workspace = {"id": workspaces[0][0], "name": workspaces[0][1]}
    
    context = {
        "request": request,
        "workspaces": [
            {"id": w[0], "name": w[1]} for w in workspaces
        ],
        "current_workspace": current_workspace,
    }
    
    templates = request.app.state.templates
    return templates.TemplateResponse("pages/audit.html", context)


@router.get("/search", response_class=HTMLResponse)
async def audit_search(
    request: Request,
    file_path: str = Query(...),
    workspace_id: int = Query(...),
    audit: AuditLogService = Depends(get_audit_service),
):
    """Search for file audit history."""
    try:
        # Get full history
        history = audit.get_file_history(workspace_id, file_path)
        
        if not history:
            return HTMLResponse("""
                <div class="text-gray-400 text-center py-4">
                    No file operations found for this path.
                </div>
            """)
        
        # Calculate stats
        total_ops = len(history)
        edit_count = sum(1 for h in history if h['action'] == 'edit')
        create_entry = next((h for h in history if h['action'] == 'create'), None)
        first_created = create_entry['created_at'] if create_entry else history[-1]['created_at']
        current_size = history[0]['file_size_bytes'] if history else 0
        
        # Parse diff_summary JSON
        for entry in history:
            if entry.get('diff_summary'):
                try:
                    entry['diff_summary'] = json.loads(entry['diff_summary'])
                except (json.JSONDecodeError, TypeError):
                    entry['diff_summary'] = None
        
        context = {
            "file_path": file_path,
            "history": history,
            "total_ops": total_ops,
            "edit_count": edit_count,
            "first_created": first_created,
            "current_size": current_size,
        }
        
        templates = request.app.state.templates
        return templates.TemplateResponse("partials/audit_results.html", context)
        
    except Exception as e:
        return HTMLResponse(f"""
            <div class="text-red-400 text-center py-4">
                Error: {str(e)}
            </div>
        """)


@router.get("/recent", response_class=HTMLResponse)
async def audit_recent(
    request: Request,
    workspace_id: Optional[int] = Query(None),
    limit: int = Query(10),
    audit: AuditLogService = Depends(get_audit_service),
):
    """Get recent file operations."""
    try:
        if not workspace_id:
            # Get first workspace as default
            db = get_sync_connection()
            result = db.execute(
                "SELECT id FROM workspaces ORDER BY id LIMIT 1"
            ).fetchone()
            workspace_id = result[0] if result else 1
        
        history = audit.get_workspace_history(workspace_id, limit=limit)
        
        if not history:
            return HTMLResponse("""
                <div class="text-gray-400 text-center py-4">
                    No recent file operations.
                </div>
            """)
        
        # Parse diff_summary JSON
        for entry in history:
            if entry.get('diff_summary'):
                try:
                    entry['diff_summary'] = json.loads(entry['diff_summary'])
                except (json.JSONDecodeError, TypeError):
                    entry['diff_summary'] = None
        
        context = {"history": history}
        
        html_parts = []
        for entry in history:
            action_color = {
                'create': 'text-green-400',
                'edit': 'text-blue-400',
                'delete': 'text-red-400',
                'rename': 'text-purple-400',
                'move': 'text-yellow-400',
            }.get(entry['action'], 'text-gray-400')
            
            timestamp = format_wib(from_iso_utc(entry['created_at']))
            
            html_parts.append(f"""
                <div class="flex gap-3 p-3 bg-gray-800 rounded-lg border border-gray-700 hover:bg-gray-750 transition-colors">
                    <div class="text-xs text-gray-400 whitespace-nowrap pt-1">{timestamp}</div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="px-2 py-0.5 rounded text-xs font-bold bg-gray-700 {action_color}">
                                {entry['action'].upper()}
                            </span>
                            <span class="text-xs text-gray-400">by {entry['source_type']}</span>
                        </div>
                        <div class="text-sm text-gray-300 truncate font-mono">{entry['file_path']}</div>
                        {f'<div class="text-xs text-gray-400 mt-1">{entry["source_description"]}</div>' if entry.get('source_description') else ''}
                    </div>
                    <div class="text-xs text-gray-400 whitespace-nowrap pt-1">{entry['file_size_bytes']} B</div>
                </div>
            """)
        
        return HTMLResponse("".join(html_parts))
        
    except Exception as e:
        return HTMLResponse(f"""
            <div class="text-red-400 text-center py-4">
                Error: {str(e)}
            </div>
        """)

