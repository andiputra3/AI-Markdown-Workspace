"""
Chat router for AI Markdown Workspace.
Handles all chat-related endpoints including send, edit, delete, copy, and streaming.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, timezone

from app.database import get_db_session
from app.services.ai_client import get_ai_client, AIClient
from app.services.markdown_engine import get_markdown_engine
from app.services.timezone_service import utc_now, to_iso_utc, from_iso_utc

router = APIRouter()

# Templates will be set by main.py
_templates: Jinja2Templates = None


def set_templates(templates: Jinja2Templates):
    """Set templates instance for this router."""
    global _templates
    _templates = templates


def get_templates() -> Jinja2Templates:
    """Get templates instance."""
    if _templates is None:
        raise RuntimeError("Templates not initialized. Call set_templates() first.")
    return _templates


async def get_current_session(db, workspace_id: int = 1) -> dict:
    """Get or create current chat session for workspace."""
    async with db.execute(
        "SELECT * FROM chat_sessions WHERE workspace_id = ? ORDER BY updated_at DESC LIMIT 1",
        (workspace_id,)
    ) as cursor:
        session = await cursor.fetchone()
        
        if not session:
            # Create new session
            now = to_iso_utc(utc_now())
            cursor = await db.execute(
                """INSERT INTO chat_sessions (workspace_id, title, model, thinking_mode, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (workspace_id, "New Chat", "mimo-v2.5", "off", now, now)
            )
            await db.commit()
            session_id = cursor.lastrowid
            
            async with db.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)) as c:
                session = await c.fetchone()
        
        return dict(session)


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Render main chat page."""
    async with get_db_session() as db:
        # Get workspaces
        async with db.execute("SELECT * FROM workspaces ORDER BY name") as cursor:
            workspaces = [dict(row) for row in await cursor.fetchall()]
        
        # Get or create current session
        workspace_id = request.query_params.get("workspace_id", 1)
        session = await get_current_session(db, int(workspace_id))
        
        # Get messages for this session
        async with db.execute(
            """SELECT * FROM messages 
               WHERE session_id = ? 
               ORDER BY created_at ASC""",
            (session["id"],)
        ) as cursor:
            messages = [dict(row) for row in await cursor.fetchall()]
        
        # Process code blocks for AI messages
        ai_client = get_ai_client()
        for msg in messages:
            if msg["role"] == "assistant":
                msg["code_blocks"] = await ai_client.extract_code_blocks(msg["content"])
                if not msg.get("raw_content"):
                    msg["raw_content"] = msg["content"]
        
        # Get current workspace
        current_workspace = None
        if workspaces:
            current_workspace = next((w for w in workspaces if w["id"] == int(workspace_id)), workspaces[0])
        
        return get_templates().TemplateResponse(
            "pages/chat.html",
            {
                "request": request,
                "session_id": session["id"],
                "messages": messages,
                "workspaces": workspaces,
                "current_workspace_id": current_workspace["id"] if current_workspace else 1,
                "current_workspace_name": current_workspace["name"] if current_workspace else "Default",
                "active_page": "chat",
                "page_title": "Chat",
            }
        )


@router.post("/send", response_class=HTMLResponse)
async def send_message(
    request: Request,
    content: str = Form(...),
    session_id: int = Form(...),
    model: str = Form("mimo-v2.5"),
    thinking: str = Form("off"),
    generate_file: bool = Form(False),
    auto_save: bool = Form(True),
):
    """Send a message and get AI response."""
    if not content.strip():
        return ""
    
    async with get_db_session() as db:
        now = to_iso_utc(utc_now())
        
        # Save user message
        cursor = await db.execute(
            """INSERT INTO messages (session_id, role, content, raw_content, created_at)
               VALUES (?, 'user', ?, ?, ?)""",
            (session_id, content, content, now)
        )
        await db.commit()
        user_msg_id = cursor.lastrowid
        
        # Get conversation history
        async with db.execute(
            """SELECT role, content FROM messages 
               WHERE session_id = ? 
               ORDER BY created_at ASC""",
            (session_id,)
        ) as cursor:
            messages = [dict(row) for row in await cursor.fetchall()]
        
        # Call AI
        ai_client = get_ai_client()
        try:
            response = await ai_client.generate_response(
                prompt=content,
                model=model,
                thinking_mode=thinking,
            )
        except Exception as e:
            return f'<div class="text-red-400 p-4">Error: {str(e)}</div>'
        
        # Save AI response
        now = to_iso_utc(utc_now())
        cursor = await db.execute(
            """INSERT INTO messages (session_id, role, content, raw_content, model, created_at)
               VALUES (?, 'assistant', ?, ?, ?, ?)""",
            (session_id, response, response, model, now)
        )
        await db.commit()
        ai_msg_id = cursor.lastrowid
        
        # Update session timestamp
        await db.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )
        await db.commit()
        
        # Extract code blocks
        code_blocks = await ai_client.extract_code_blocks(response)
        
        # Render AI message bubble
        ai_msg = {
            "id": ai_msg_id,
            "content": response,
            "raw_content": response,
            "model": model,
            "created_at": now,
            "code_blocks": code_blocks,
        }
        
        templates: Jinja2Templates = get_templates()
        return templates.get_template("components/chat_message_ai.html").render({
            "msg": ai_msg,
            "session_id": session_id,
        })


@router.get("/stream")
async def stream_chat(request: Request, session_id: int):
    """Stream AI response via Server-Sent Events."""
    async def event_generator():
        # This is a simplified version - full implementation would track streaming state
        yield f"data: {json.dumps({'chunk': ''})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/message/{message_id}/edit", response_class=HTMLResponse)
async def edit_message_form(request: Request, message_id: int):
    """Return edit form for a message."""
    async with get_db_session() as db:
        async with db.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ) as cursor:
            msg = dict(await cursor.fetchone())
        
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        
        templates: Jinja2Templates = get_templates()
        return templates.get_template("partials/message_edit.html").render({
            "msg": msg,
        })


@router.post("/message/{message_id}/save", response_class=HTMLResponse)
async def save_edited_message(
    request: Request,
    message_id: int,
    content: str = Form(...),
):
    """Save edited message and regenerate response."""
    async with get_db_session() as db:
        now = to_iso_utc(utc_now())
        
        # Update message
        await db.execute(
            """UPDATE messages 
               SET content = ?, raw_content = COALESCE(raw_content, content), 
                   is_edited = 1, edited_at = ?
               WHERE id = ?""",
            (content, now, message_id)
        )
        await db.commit()
        
        # Get updated message
        async with db.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ) as cursor:
            msg = dict(await cursor.fetchone())
        
        # Regenerate AI response (simplified)
        ai_client = get_ai_client()
        response = await ai_client.generate_response(prompt=content)
        
        # Return updated bubble
        templates: Jinja2Templates = get_templates()
        return templates.get_template("components/chat_message_user.html").render({
            "msg": msg,
        })


@router.post("/message/{message_id}/regenerate", response_class=HTMLResponse)
async def regenerate_message(request: Request, message_id: int):
    """Regenerate AI response for a message."""
    async with get_db_session() as db:
        # Get the user message before this AI message
        async with db.execute(
            """SELECT m1.*, m2.id as ai_msg_id
               FROM messages m1
               LEFT JOIN messages m2 ON m2.session_id = m1.session_id 
                   AND m2.role = 'assistant' 
                   AND m2.created_at > m1.created_at
               WHERE m1.id = ?""",
            (message_id,)
        ) as cursor:
            result = await cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Message not found")
        
        user_msg = dict(result)
        ai_msg_id = result.get("ai_msg_id")
        
        # Generate new response
        ai_client = get_ai_client()
        response = await ai_client.generate_response(prompt=user_msg["content"])
        
        now = to_iso_utc(utc_now())
        
        if ai_msg_id:
            # Update existing AI message
            await db.execute(
                "UPDATE messages SET content = ?, raw_content = ?, created_at = ? WHERE id = ?",
                (response, response, now, ai_msg_id)
            )
        else:
            # Insert new AI message
            cursor = await db.execute(
                """INSERT INTO messages (session_id, role, content, raw_content, created_at)
                   VALUES (?, 'assistant', ?, ?, ?)""",
                (user_msg["session_id"], response, response, now)
            )
            await db.commit()
            ai_msg_id = cursor.lastrowid
        
        # Get updated AI message
        async with db.execute(
            "SELECT * FROM messages WHERE id = ?", (ai_msg_id,)
        ) as cursor:
            ai_msg = dict(await cursor.fetchone())
        
        code_blocks = await ai_client.extract_code_blocks(response)
        ai_msg["code_blocks"] = code_blocks
        
        templates: Jinja2Templates = get_templates()
        return templates.get_template("components/chat_message_ai.html").render({
            "msg": ai_msg,
            "session_id": user_msg["session_id"],
        })


@router.post("/copy-all")
async def copy_all_chat(request: Request):
    """Copy entire chat to clipboard (returns toast notification)."""
    return '<div class="bg-green-600 text-white px-4 py-2 rounded shadow">✓ Chat copied!</div>'


@router.get("/new")
async def new_chat(request: Request, workspace_id: int = 1):
    """Create a new chat session."""
    async with get_db_session() as db:
        now = to_iso_utc(utc_now())
        cursor = await db.execute(
            """INSERT INTO chat_sessions (workspace_id, title, model, thinking_mode, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (workspace_id, "New Chat", "mimo-v2.5", "off", now, now)
        )
        await db.commit()
        new_session_id = cursor.lastrowid
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/chat?session_id={new_session_id}")
