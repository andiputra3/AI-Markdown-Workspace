"""
Database connection and schema initialization for AI Markdown Workspace.
Uses SQLite with async support via aiosqlite.
All timestamps stored as UTC ISO 8601 strings.
"""
import sqlite3
import aiosqlite
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from app.config import settings


DATABASE_PATH = Path(settings.DATABASE_PATH)


def get_sync_connection() -> sqlite3.Connection:
    """Get synchronous SQLite connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """FastAPI dependency for database session (synchronous)."""
    db = get_sync_connection()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for database sessions."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """Initialize database schema with all tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # ========== WORKSPACES ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # ========== CHAT SESSIONS ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                title TEXT DEFAULT 'New Chat',
                model TEXT DEFAULT 'mimo-v2.5',
                thinking_mode TEXT DEFAULT 'off',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
        """)
        
        # ========== MESSAGES ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                raw_content TEXT,
                is_edited INTEGER DEFAULT 0,
                edited_at TEXT,
                token_count INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # ========== GENERATED FILES ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS generated_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_id INTEGER,
                workspace_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            )
        """)
        
        # ========== FILE CREATION LOG (CORE FEATURE) ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_creation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                previous_path TEXT,
                action TEXT NOT NULL CHECK(action IN (
                    'create', 'edit', 'delete', 'rename', 'move',
                    'restore', 'import', 'export', 'generate'
                )),
                source_type TEXT NOT NULL CHECK(source_type IN (
                    'chat_message', 'builder_command', 'manual',
                    'import', 'system'
                )),
                source_id INTEGER,
                source_description TEXT,
                file_size_bytes INTEGER,
                line_count INTEGER,
                md5_hash TEXT,
                language_detected TEXT,
                diff_summary TEXT,
                user_agent TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
                FOREIGN KEY (source_id) REFERENCES messages(id)
            )
        """)
        
        # Create indexes for file_creation_log
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_log_workspace 
            ON file_creation_log(workspace_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_log_path 
            ON file_creation_log(file_path)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_log_created 
            ON file_creation_log(created_at)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_log_action 
            ON file_creation_log(action)
        """)
        
        # ========== SETTINGS ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # ========== BUILDER TEMPLATES ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS builder_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                prompt_template TEXT NOT NULL,
                output_filename TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # ========== RAG INDEX ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rag_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding BLOB,
                chunk_index INTEGER,
                indexed_at TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            )
        """)
        
        # ========== TOKEN USAGE ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                message_id INTEGER,
                model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        """)
        
        # ========== INSERT DEFAULT BUILDER TEMPLATES ==========
        now = datetime.now(timezone.utc).isoformat()
        builders = [
            (
                '/spec-builder', 'Specification Builder',
                'Generate SPECIFICATION.md for a project',
                'Create a comprehensive SPECIFICATION.md for project "{project_name}". Include: 1) Project Overview 2) Features 3) Tech Stack 4) Database Schema 5) API Endpoints 6) File Structure 7) Milestones. Output clean Markdown.',
                'SPECIFICATION.md'
            ),
            (
                '/plan-builder', 'Planning Builder',
                'Generate BUILD_PLAN.md',
                'Create a detailed BUILD_PLAN.md for "{project_name}" based on its specification. Include: Phase breakdown, tasks per phase, dependencies, estimated time, priority.',
                'BUILD_PLAN.md'
            ),
            (
                '/sqlite-builder', 'SQLite Builder',
                'Generate schema.sql',
                'Design complete SQLite schema for "{project_name}". Include CREATE TABLE, indexes, foreign keys, seed data. Output as single SQL code block.',
                'schema.sql'
            ),
            (
                '/api-builder', 'API Builder',
                'Generate API.md',
                'Design REST API for "{project_name}". Include: method, path, request/response bodies, status codes. Output as Markdown tables + JSON examples.',
                'API.md'
            ),
            (
                '/doc-builder', 'Documentation Builder',
                'Generate README.md',
                'Create README.md + DOCUMENTATION.md for "{project_name}". Include: install, usage, architecture, API, contributing.',
                'README.md'
            ),
            (
                '/roadmap-builder', 'Roadmap Builder',
                'Generate ROADMAP.md',
                'Create ROADMAP.md for "{project_name}" with: version milestones, feature timeline, breaking changes, future vision.',
                'ROADMAP.md'
            ),
            (
                '/audit-file', 'File Audit',
                'Audit history of a specific file',
                'Analyze the file creation log for "{file_path}" in workspace "{workspace_name}". Provide: 1) Creation summary 2) Timeline of all operations 3) Edit frequency 4) Size growth 5) Most active contributors (sources). Output as Markdown report.',
                None
            ),
        ]
        
        for command, name, desc, template, filename in builders:
            await db.execute("""
                INSERT OR IGNORE INTO builder_templates 
                (command, name, description, prompt_template, output_filename, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (command, name, desc, template, filename, now))
        
        # ========== INSERT DEFAULT SETTINGS ==========
        default_settings = [
            ('ai_api_endpoint', settings.AI_API_ENDPOINT),
            ('ai_api_key', settings.AI_API_KEY or ''),
            ('ai_model', settings.AI_MODEL),
            ('ai_temperature', str(settings.AI_TEMPERATURE)),
            ('ai_max_tokens', str(settings.AI_MAX_TOKENS)),
            ('ai_thinking_mode', settings.AI_THINKING_MODE),
            ('markdown_extensions', ','.join(settings.MARKDOWN_EXTENSIONS)),
            ('rag_enabled', '1' if settings.RAG_ENABLED else '0'),
            ('tool_call_enabled', '1' if settings.TOOL_CALL_ENABLED else '0'),
            ('mcp_enabled', '1' if settings.MCP_ENABLED else '0'),
        ]
        
        for key, value in default_settings:
            await db.execute("""
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
        
        await db.commit()
        
        print(f"Database initialized at {DATABASE_PATH}")


async def reset_db() -> None:
    """Reset database by dropping all tables (for development only)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        tables = [
            'token_usage', 'rag_index', 'builder_templates', 'settings',
            'file_creation_log', 'generated_files', 'messages',
            'chat_sessions', 'workspaces'
        ]
        for table in tables:
            await db.execute(f"DROP TABLE IF EXISTS {table}")
        await db.commit()
        print("Database reset complete")
