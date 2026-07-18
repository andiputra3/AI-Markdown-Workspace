"""
File Manager Service for AI Markdown Workspace.
Handles file operations with automatic audit logging.
All file operations are logged via AuditLogService.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.config import settings
from app.services.audit_log import AuditLogService
from app.services.timezone_service import utc_now, to_iso_utc


class FileManager:
    """
    File manager service with integrated audit logging.
    
    Every file operation (create, edit, delete, rename) is automatically
    logged to the file_creation_log table via AuditLogService.
    
    Features:
    - Workspace-based file organization
    - Safe path handling (no directory traversal)
    - Automatic language detection
    - Full audit trail
    """
    
    def __init__(self, audit_log: Optional[AuditLogService] = None):
        """
        Initialize file manager.
        
        Args:
            audit_log: AuditLogService instance for logging
        """
        self.audit = audit_log or AuditLogService()
        self.workspaces_root = Path(settings.WORKSPACES_ROOT)
        self.max_file_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        
        # Ensure workspaces root exists
        self.workspaces_root.mkdir(parents=True, exist_ok=True)
    
    def _get_workspace_path(self, workspace_id: int, workspace_name: str) -> Path:
        """
        Get workspace directory path.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name (for path construction)
            
        Returns:
            Path: Workspace directory path
        """
        # Use workspace name for directory (more user-friendly)
        workspace_path = self.workspaces_root / workspace_name
        workspace_path.mkdir(parents=True, exist_ok=True)
        return workspace_path
    
    def _safe_path(self, workspace_path: Path, file_path: str) -> Path:
        """
        Safely resolve file path preventing directory traversal.
        
        Args:
            workspace_path: Base workspace path
            file_path: Relative file path
            
        Returns:
            Path: Resolved absolute path
            
        Raises:
            ValueError: If path attempts directory traversal
        """
        # Normalize and resolve the path
        full_path = (workspace_path / file_path).resolve()
        
        # Ensure path is within workspace
        if not str(full_path).startswith(str(workspace_path.resolve())):
            raise ValueError(f"Invalid file path: {file_path} (directory traversal detected)")
        
        return full_path
    
    def _detect_language(self, filename: str) -> Optional[str]:
        """
        Detect programming language from filename extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Detected language name or None
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.ps1': 'powershell',
            '.txt': 'text',
            '.xml': 'xml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.env': 'dotenv',
            '.dockerfile': 'dockerfile',
            '.gitignore': 'gitignore',
        }
        
        ext = Path(filename).suffix.lower()
        return ext_map.get(ext)
    
    async def create_file(
        self,
        workspace_id: int,
        workspace_name: str,
        file_path: str,
        content: str,
        source_type: str = 'manual',
        source_id: Optional[int] = None,
        source_description: str = "",
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new file with audit logging.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            file_path: Relative path to file
            content: File content
            source_type: Source type (chat_message, builder_command, manual, etc.)
            source_id: Source ID (e.g., message_id)
            source_description: Human-readable source description
            user_agent: Browser/session info
            
        Returns:
            dict: File info with path, size, language
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        full_path = self._safe_path(workspace_path, file_path)
        
        # Check file size
        if len(content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB")
        
        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        full_path.write_text(content, encoding='utf-8')
        
        # Detect language
        language = self._detect_language(file_path)
        
        # Log to audit (sync call, no await needed)
        self.audit.log_create(
            workspace_id=workspace_id,
            file_path=file_path,
            content=content,
            source_type=source_type,
            source_id=source_id,
            source_description=source_description,
            language=language,
            user_agent=user_agent,
        )
        
        return {
            'path': file_path,
            'full_path': str(full_path),
            'size': len(content.encode('utf-8')),
            'lines': len(content.splitlines()),
            'language': language,
        }
    
    async def read_file(
        self,
        workspace_id: int,
        workspace_name: str,
        file_path: str,
    ) -> str:
        """
        Read file content.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            file_path: Relative path to file
            
        Returns:
            str: File content
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        full_path = self._safe_path(workspace_path, file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.read_text(encoding='utf-8')
    
    async def edit_file(
        self,
        workspace_id: int,
        workspace_name: str,
        file_path: str,
        new_content: str,
        source_type: str = 'manual',
        source_id: Optional[int] = None,
        source_description: str = "",
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Edit existing file with audit logging.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            file_path: Relative path to file
            new_content: New file content
            source_type: Source type
            source_id: Source ID
            source_description: Source description
            user_agent: User agent string
            
        Returns:
            dict: File info with changes
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        full_path = self._safe_path(workspace_path, file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read old content
        old_content = full_path.read_text(encoding='utf-8')
        
        # Check file size
        if len(new_content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB")
        
        # Write new content
        full_path.write_text(new_content, encoding='utf-8')
        
        # Log to audit (sync call, no await needed)
        self.audit.log_edit(
            workspace_id=workspace_id,
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            source_type=source_type,
            source_id=source_id,
            source_description=source_description,
            user_agent=user_agent,
        )
        
        return {
            'path': file_path,
            'old_size': len(old_content.encode('utf-8')),
            'new_size': len(new_content.encode('utf-8')),
            'old_lines': len(old_content.splitlines()),
            'new_lines': len(new_content.splitlines()),
        }
    
    async def delete_file(
        self,
        workspace_id: int,
        workspace_name: str,
        file_path: str,
        source_type: str = 'manual',
        source_description: str = "",
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Delete file with audit logging.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            file_path: Relative path to file
            source_type: Source type
            source_description: Source description
            user_agent: User agent string
            
        Returns:
            bool: True if deleted
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        full_path = self._safe_path(workspace_path, file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Delete file
        full_path.unlink()
        
        # Log to audit (sync call, no await needed)
        self.audit.log_delete(
            workspace_id=workspace_id,
            file_path=file_path,
            source_type=source_type,
            source_description=source_description,
            user_agent=user_agent,
        )
        
        return True
    
    async def rename_file(
        self,
        workspace_id: int,
        workspace_name: str,
        old_path: str,
        new_path: str,
        source_type: str = 'manual',
        source_description: str = "",
        user_agent: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Rename/move file with audit logging.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            old_path: Current file path
            new_path: New file path
            source_type: Source type
            source_description: Source description
            user_agent: User agent string
            
        Returns:
            dict: Old and new paths
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        old_full_path = self._safe_path(workspace_path, old_path)
        new_full_path = self._safe_path(workspace_path, new_path)
        
        if not old_full_path.exists():
            raise FileNotFoundError(f"File not found: {old_path}")
        
        # Create parent directories for new path
        new_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(old_full_path), str(new_full_path))
        
        # Log to audit (sync call, no await needed)
        self.audit.log_rename(
            workspace_id=workspace_id,
            old_path=old_path,
            new_path=new_path,
            source_type=source_type,
            source_description=source_description,
            user_agent=user_agent,
        )
        
        return {
            'old_path': old_path,
            'new_path': new_path,
        }
    
    async def list_files(
        self,
        workspace_id: int,
        workspace_name: str,
        base_path: str = "",
    ) -> List[Dict[str, Any]]:
        """
        List files in workspace directory.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            base_path: Subdirectory to list (empty for root)
            
        Returns:
            list: File/directory info dicts
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        
        if base_path:
            current_path = self._safe_path(workspace_path, base_path)
        else:
            current_path = workspace_path
        
        if not current_path.exists():
            return []
        
        items = []
        for item in sorted(current_path.iterdir()):
            rel_path = str(item.relative_to(workspace_path))
            is_dir = item.is_dir()
            
            file_info = {
                'name': item.name,
                'path': rel_path,
                'is_directory': is_dir,
                'type': 'folder' if is_dir else 'file',
            }
            
            if not is_dir:
                try:
                    stat = item.stat()
                    file_info['size'] = stat.st_size
                    file_info['modified'] = datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat()
                    file_info['language'] = self._detect_language(item.name)
                except Exception:
                    pass
            
            items.append(file_info)
        
        return items
    
    async def file_exists(
        self,
        workspace_id: int,
        workspace_name: str,
        file_path: str,
    ) -> bool:
        """
        Check if file exists.
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Workspace name
            file_path: Relative path to file
            
        Returns:
            bool: True if file exists
        """
        workspace_path = self._get_workspace_path(workspace_id, workspace_name)
        try:
            full_path = self._safe_path(workspace_path, file_path)
            return full_path.exists()
        except ValueError:
            return False


# Global instance
file_manager = FileManager()


def get_file_manager() -> FileManager:
    """Dependency function to get file manager instance."""
    return file_manager
