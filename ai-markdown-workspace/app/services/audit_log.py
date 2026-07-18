"""
Audit Log Service for AI Markdown Workspace.
Logs every file operation with full metadata for tracking and auditing.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3

from app.database import get_sync_connection
from app.services.timezone_service import utc_now, to_iso_utc


class AuditLogService:
    """
    Service for logging and retrieving file operation history.
    
    Every file create/edit/delete/rename/move operation is logged
    with full metadata including hash, size, line count, and source.
    """
    
    def __init__(self, db=None):
        """Initialize the audit log service."""
        self.db = db if db else get_sync_connection()
    
    def _compute_hash(self, content: str) -> str:
        """Compute MD5 hash of file content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _count_lines(self, content: str) -> int:
        """Count lines in content."""
        return len(content.splitlines())
    
    def _compute_diff_summary(self, old_content: str, new_content: str) -> Dict[str, int]:
        """Compute simple diff summary (lines added/removed)."""
        old_lines = set(old_content.splitlines())
        new_lines = set(new_content.splitlines())
        added = len(new_lines - old_lines)
        removed = len(old_lines - new_lines)
        return {'added': added, 'removed': removed}
    
    def log_create(self, workspace_id: int, file_path: str, content: str,
                   source_type: str, source_id: Optional[int] = None,
                   source_description: str = "", language: Optional[str] = None,
                   user_agent: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> int:
        """Log file creation."""
        file_size = len(content.encode('utf-8'))
        line_count = self._count_lines(content)
        md5_hash = self._compute_hash(content)
        created_at = to_iso_utc(utc_now())
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor = self.db.execute("""
            INSERT INTO file_creation_log (
                workspace_id, file_path, action, source_type,
                source_id, source_description, file_size_bytes,
                line_count, md5_hash, language_detected,
                user_agent, metadata_json, created_at
            ) VALUES (?, ?, 'create', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (workspace_id, file_path, source_type, source_id,
              source_description, file_size, line_count, md5_hash,
              language, user_agent, metadata_json, created_at))
        self.db.commit()
        return cursor.lastrowid
    
    def log_edit(self, workspace_id: int, file_path: str,
                 old_content: str, new_content: str,
                 source_type: str, source_id: Optional[int] = None,
                 source_description: str = "",
                 user_agent: Optional[str] = None) -> int:
        """Log file edit with diff summary."""
        file_size = len(new_content.encode('utf-8'))
        line_count = self._count_lines(new_content)
        md5_hash = self._compute_hash(new_content)
        diff_summary = self._compute_diff_summary(old_content, new_content)
        created_at = to_iso_utc(utc_now())
        
        cursor = self.db.execute("""
            INSERT INTO file_creation_log (
                workspace_id, file_path, action, source_type,
                source_id, source_description, file_size_bytes,
                line_count, md5_hash, diff_summary,
                user_agent, created_at
            ) VALUES (?, ?, 'edit', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (workspace_id, file_path, source_type, source_id,
              source_description, file_size, line_count, md5_hash,
              json.dumps(diff_summary), user_agent, created_at))
        self.db.commit()
        return cursor.lastrowid
    
    def log_delete(self, workspace_id: int, file_path: str,
                   source_type: str = 'manual',
                   source_description: str = "") -> int:
        """Log file deletion."""
        created_at = to_iso_utc(utc_now())
        cursor = self.db.execute("""
            INSERT INTO file_creation_log (
                workspace_id, file_path, action, source_type,
                source_description, created_at
            ) VALUES (?, ?, 'delete', ?, ?, ?)
        """, (workspace_id, file_path, source_type, source_description, created_at))
        self.db.commit()
        return cursor.lastrowid
    
    def log_rename(self, workspace_id: int, old_path: str, new_path: str,
                   source_type: str = 'manual',
                   source_description: str = "") -> int:
        """Log rename/move."""
        created_at = to_iso_utc(utc_now())
        cursor = self.db.execute("""
            INSERT INTO file_creation_log (
                workspace_id, file_path, previous_path, action,
                source_type, source_description, created_at
            ) VALUES (?, ?, ?, 'rename', ?, ?, ?)
        """, (workspace_id, new_path, old_path, source_type,
              source_description, created_at))
        self.db.commit()
        return cursor.lastrowid
    
    def get_file_history(self, workspace_id: int, file_path: str) -> List[dict]:
        """Get full history of a specific file."""
        cursor = self.db.execute("""
            SELECT * FROM file_creation_log
            WHERE workspace_id = ? AND file_path = ?
            ORDER BY created_at DESC
        """, (workspace_id, file_path))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_workspace_history(self, workspace_id: int, limit: int = 100) -> List[dict]:
        """Get recent file operations in workspace."""
        cursor = self.db.execute("""
            SELECT * FROM file_creation_log
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (workspace_id, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_audit_report(self, workspace_id: int, file_path: str) -> dict:
        """Generate comprehensive audit report for a file."""
        history = self.get_file_history(workspace_id, file_path)
        
        if not history:
            return {'error': 'No history found'}
        
        # Find first creation
        creates = [h for h in history if h['action'] == 'create']
        first_created = creates[-1]['created_at'] if creates else None
        
        # Count edits
        edits = [h for h in history if h['action'] == 'edit']
        edit_count = len(edits)
        
        # Calculate size growth
        sizes = [(h['created_at'], h['file_size_bytes']) for h in history if h['file_size_bytes']]
        current_size = sizes[0][1] if sizes else 0
        
        # Source messages
        sources = {}
        for h in history:
            src = h['source_type']
            sources[src] = sources.get(src, 0) + 1
        
        return {
            'file_path': file_path,
            'first_created': first_created,
            'total_ops': len(history),
            'edit_count': edit_count,
            'current_size': current_size,
            'sources': sources,
            'history': history
        }
