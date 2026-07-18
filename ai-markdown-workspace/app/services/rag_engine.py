"""
RAG Engine for AI Markdown Workspace.
Provides contextual retrieval-augmented generation at workspace level.
"""
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path


class RAGEngine:
    """
    Simple RAG engine for workspace-level context.
    
    Features:
    - Chunk-based indexing of workspace files
    - SQLite storage for chunks (no external vector DB required)
    - Keyword-based retrieval (embedding support optional)
    """
    
    def __init__(self, db_path: str = "data/workspace.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    async def index_file(
        self,
        workspace_id: int,
        file_path: str,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """
        Index a file by splitting into chunks.
        
        Args:
            workspace_id: Workspace ID
            file_path: Relative file path
            content: File content
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            int: Number of chunks created
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete existing chunks for this file
        cursor.execute(
            "DELETE FROM rag_index WHERE workspace_id = ? AND file_path = ?",
            (workspace_id, file_path)
        )
        
        # Split content into chunks
        chunks = self._split_content(content, chunk_size, chunk_overlap)
        
        # Insert chunks
        count = 0
        for i, chunk in enumerate(chunks):
            cursor.execute(
                """INSERT INTO rag_index 
                   (workspace_id, file_path, chunk_text, chunk_index, indexed_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (workspace_id, file_path, chunk, i)
            )
            count += 1
        
        conn.commit()
        conn.close()
        return count
    
    def _split_content(
        self, 
        content: str, 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[str]:
        """Split content into overlapping chunks."""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start += chunk_size - chunk_overlap
        
        return chunks
    
    async def search(
        self,
        workspace_id: int,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks in workspace.
        
        Args:
            workspace_id: Workspace ID
            query: Search query
            limit: Max results
            
        Returns:
            list: Matching chunks with metadata
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Simple keyword search (can be enhanced with embeddings)
        query_terms = query.lower().split()
        results = []
        
        cursor.execute(
            """SELECT id, file_path, chunk_text, chunk_index, indexed_at
               FROM rag_index
               WHERE workspace_id = ?""",
            (workspace_id,)
        )
        
        rows = cursor.fetchall()
        
        # Score chunks by keyword matches
        for row in rows:
            chunk_lower = row['chunk_text'].lower()
            score = sum(1 for term in query_terms if term in chunk_lower)
            
            if score > 0:
                results.append({
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'chunk_text': row['chunk_text'],
                    'chunk_index': row['chunk_index'],
                    'indexed_at': row['indexed_at'],
                    'score': score,
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        conn.close()
        
        return results[:limit]
    
    async def get_indexed_files(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Get list of indexed files in workspace."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT file_path, COUNT(*) as chunk_count, 
                      MAX(indexed_at) as last_indexed
               FROM rag_index
               WHERE workspace_id = ?
               GROUP BY file_path""",
            (workspace_id,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'file_path': row['file_path'],
                'chunk_count': row['chunk_count'],
                'last_indexed': row['last_indexed'],
            }
            for row in rows
        ]
    
    async def clear_index(self, workspace_id: int) -> bool:
        """Clear RAG index for workspace."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM rag_index WHERE workspace_id = ?",
            (workspace_id,)
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0


# Global instance
rag_engine = RAGEngine()


def get_rag_engine() -> RAGEngine:
    """Dependency function to get RAG engine instance."""
    return rag_engine
