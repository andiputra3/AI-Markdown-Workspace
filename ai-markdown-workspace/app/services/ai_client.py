"""
AI Client Service for AI Markdown Workspace.
OpenAI-compatible HTTP client with SSE streaming support.
Supports Ollama, vLLM, MiMo, OpenAI, and other compatible backends.
"""
import json
import httpx
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime, timezone

from app.config import settings
from app.services.timezone_service import utc_now, to_iso_utc


class AIClient:
    """
    OpenAI-compatible AI client with streaming support.
    
    Supports:
    - Chat completions (non-streaming)
    - Streaming responses via SSE
    - Multiple models
    - Thinking mode configuration
    """
    
    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
    ):
        """
        Initialize the AI client.
        
        Args:
            api_endpoint: Base URL for AI API (e.g., http://localhost:11434/v1)
            api_key: API key (optional for local models)
            model: Default model name
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            thinking_mode: Thinking mode (off, low, high)
        """
        self.api_endpoint = api_endpoint or settings.AI_API_ENDPOINT
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.max_tokens = max_tokens or settings.AI_MAX_TOKENS
        self.thinking_mode = thinking_mode or settings.AI_THINKING_MODE
        
        # Remove trailing /v1 for base URL construction
        self.base_url = self.api_endpoint.rstrip('/')
        
        # Ensure endpoint ends with /v1 for API calls
        if not self.api_endpoint.endswith('/v1'):
            self.api_endpoint = f"{self.api_endpoint.rstrip('/')}/v1"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (overrides default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            thinking_mode: Thinking mode
            stream: Whether to stream response
            
        Returns:
            dict: Response from AI API
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
        }
        
        # Add thinking mode if supported
        tm = thinking_mode or self.thinking_mode
        if tm and tm != 'off':
            # Some models support thinking/reasoning modes
            payload["thinking"] = {"mode": tm}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_endpoint}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        session_id: int,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response using Server-Sent Events.
        
        Args:
            messages: List of message dicts
            session_id: Chat session ID for tracking
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            thinking_mode: Thinking mode
            
        Yields:
            str: Chunks of AI response text
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": True,
        }
        
        tm = thinking_mode or self.thinking_mode
        if tm and tm != 'off':
            payload["thinking"] = {"mode": tm}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_endpoint}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data)
                            # Extract content from chunk
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
    ) -> str:
        """
        Generate a single response from AI.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            thinking_mode: Thinking mode
            
        Returns:
            str: AI response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode,
        )
        
        choices = response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""
    
    async def extract_code_blocks(
        self, content: str
    ) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown content.
        
        Args:
            content: Markdown content with code blocks
            
        Returns:
            list: List of dicts with 'language', 'code', 'filename' keys
        """
        import re
        
        code_blocks = []
        pattern = r'```(\w+)?(?:\s+([^\n]+))?\n(.*?)```'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or 'text'
            filename = match.group(2) or ''
            code = match.group(3).strip()
            
            code_blocks.append({
                'language': language,
                'filename': filename.strip() if filename else '',
                'code': code,
            })
        
        return code_blocks
    
    async def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).
        
        Args:
            text: Input text
            
        Returns:
            int: Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters in English
        return len(text) // 4
    
    async def log_token_usage(
        self,
        session_id: int,
        message_id: int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """
        Log token usage to database.
        
        Args:
            session_id: Chat session ID
            message_id: Message ID
            model: Model used
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
        """
        from app.database import get_db_session
        
        total_tokens = prompt_tokens + completion_tokens
        created_at = to_iso_utc(utc_now())
        
        # Simple cost estimation (adjust per model)
        cost_per_1k = 0.002  # $0.002 per 1K tokens (approximate)
        cost_usd = (total_tokens / 1000) * cost_per_1k
        
        async with get_db_session() as db:
            await db.execute("""
                INSERT INTO token_usage (
                    session_id, message_id, model,
                    prompt_tokens, completion_tokens,
                    total_tokens, cost_usd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, message_id, model,
                prompt_tokens, completion_tokens,
                total_tokens, cost_usd, created_at
            ))
            await db.commit()


# Global instance with default settings
ai_client = AIClient()


def get_ai_client() -> AIClient:
    """Dependency function to get AI client instance."""
    return ai_client


def create_ai_client(
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> AIClient:
    """Factory function to create custom AI client."""
    return AIClient(
        api_endpoint=api_endpoint,
        api_key=api_key,
        model=model,
    )
