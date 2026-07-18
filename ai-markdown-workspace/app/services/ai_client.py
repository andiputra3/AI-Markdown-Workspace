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
    - Xiaomi Mimo Plan API specific support
    - OpenRouter API support (https://openrouter.ai/docs)
    - Tool/Function Calling
    - Model Context Protocol (MCP) integration
    """
    
    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
        use_xiaomi_mimo: bool = False,
        use_openrouter: bool = False,
        enable_tool_calling: bool = False,
        enable_mcp: bool = False,
        mcp_server_command: Optional[str] = None,
        mcp_server_args: Optional[str] = None,
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
            use_xiaomi_mimo: Use Xiaomi Mimo Plan API settings
            use_openrouter: Use OpenRouter API settings
            enable_tool_calling: Enable function/tool calling
            enable_mcp: Enable Model Context Protocol
            mcp_server_command: MCP server command (e.g., "npx mcp-server-filesystem")
            mcp_server_args: MCP server arguments as JSON string
        """
        if use_openrouter:
            # Use OpenRouter API settings
            self.api_endpoint = settings.OPENROUTER_API_ENDPOINT
            self.api_key = api_key or settings.OPENROUTER_API_KEY
            self.model = model or settings.OPENROUTER_MODEL
            self.site_url = settings.OPENROUTER_SITE_URL
            self.site_name = settings.OPENROUTER_SITE_NAME
        elif use_xiaomi_mimo:
            # Use Xiaomi Mimo Plan API settings
            self.api_endpoint = settings.XIAOMI_MIMO_API_ENDPOINT
            self.api_key = api_key or settings.XIAOMI_MIMO_API_KEY
            self.model = model or settings.XIAOMI_MIMO_MODEL
        else:
            # Use generic AI settings
            self.api_endpoint = api_endpoint or settings.AI_API_ENDPOINT
            self.api_key = api_key or settings.AI_API_KEY
            self.model = model or settings.AI_MODEL
        
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.max_tokens = max_tokens or settings.AI_MAX_TOKENS
        self.thinking_mode = thinking_mode or settings.AI_THINKING_MODE
        self.enable_tool_calling = enable_tool_calling or settings.TOOL_CALL_ENABLED
        self.enable_mcp = enable_mcp or settings.MCP_ENABLED
        self.mcp_server_command = mcp_server_command or settings.MCP_SERVER_COMMAND
        self.mcp_server_args = mcp_server_args or settings.MCP_SERVER_ARGS
        
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
        
        # Add Authorization header if API key exists
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # OpenRouter-specific headers (per OpenRouter docs)
        if hasattr(self, 'site_url') and hasattr(self, 'site_name'):
            headers["HTTP-Referer"] = self.site_url
            headers["X-Title"] = self.site_name
        
        return headers
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        thinking_mode: Optional[str] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
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
            tools: List of tool definitions for function calling
            tool_choice: Tool choice strategy ('auto', 'none', 'required', or specific tool)
            
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
        
        # Add tool calling if enabled and tools provided
        if self.enable_tool_calling and tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
            elif len(tools) == 1:
                payload["tool_choice"] = "auto"
        
        # OpenRouter-specific parameters
        if hasattr(self, 'site_url'):
            payload["provider"] = {
                "order": ["OpenRouter"],
                "allow_fallbacks": True,
            }
        
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
    use_xiaomi_mimo: bool = False,
    use_openrouter: bool = False,
    enable_tool_calling: bool = False,
    enable_mcp: bool = False,
    mcp_server_command: Optional[str] = None,
    mcp_server_args: Optional[str] = None,
) -> AIClient:
    """Factory function to create custom AI client.
    
    Args:
        api_endpoint: Custom API endpoint
        api_key: API key
        model: Model name
        use_xiaomi_mimo: Use Xiaomi Mimo Plan API settings
        use_openrouter: Use OpenRouter API settings
        enable_tool_calling: Enable function/tool calling
        enable_mcp: Enable Model Context Protocol
        mcp_server_command: MCP server command
        mcp_server_args: MCP server arguments as JSON string
    
    Returns:
        AIClient instance
    """
    return AIClient(
        api_endpoint=api_endpoint,
        api_key=api_key,
        model=model,
        use_xiaomi_mimo=use_xiaomi_mimo,
        use_openrouter=use_openrouter,
        enable_tool_calling=enable_tool_calling,
        enable_mcp=enable_mcp,
        mcp_server_command=mcp_server_command,
        mcp_server_args=mcp_server_args,
    )


class MCPClient:
    """
    Model Context Protocol (MCP) client for connecting to MCP servers.
    
    Supports:
    - stdio transport (spawn process and communicate via stdin/stdout)
    - SSE transport (Server-Sent Events)
    - Multiple MCP servers
    - Tool discovery and execution
    """
    
    def __init__(
        self,
        server_command: str,
        server_args: Optional[List[str]] = None,
        transport: str = "stdio",
        sse_endpoint: Optional[str] = None,
    ):
        """
        Initialize MCP client.
        
        Args:
            server_command: Command to run MCP server (e.g., "npx", "uvx")
            server_args: List of arguments for the server
            transport: Transport type ("stdio" or "sse")
            sse_endpoint: URL for SSE transport
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.transport = transport
        self.sse_endpoint = sse_endpoint
        self.process: Optional[any] = None
        self.tools: List[Dict[str, Any]] = []
    
    async def connect(self) -> None:
        """Connect to MCP server."""
        import asyncio
        
        if self.transport == "stdio":
            # Spawn process for stdio transport
            self.process = await asyncio.create_subprocess_exec(
                self.server_command,
                *self.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Initialize connection and discover tools
            await self._initialize()
            await self._list_tools()
        elif self.transport == "sse" and self.sse_endpoint:
            # Connect via SSE
            await self._connect_sse()
            await self._list_tools()
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server."""
        import json
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        
        if self.transport == "stdio" and self.process:
            # Send via stdin
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response from stdout
            response_line = await self.process.stdout.readline()
            if response_line:
                return json.loads(response_line.decode())
        
        return {"error": "No connection"}
    
    async def _initialize(self) -> None:
        """Initialize MCP connection."""
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "AI Markdown Workspace",
                "version": "1.0.0",
            },
        })
    
    async def _list_tools(self) -> None:
        """List available tools from MCP server."""
        response = await self._send_request("tools/list")
        if "result" in response and "tools" in response["result"]:
            self.tools = response["result"]["tools"]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            dict: Tool execution result
        """
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return response.get("result", {})
    
    def get_tools_as_openai_format(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function calling format."""
        openai_tools = []
        for tool in self.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {}),
                },
            })
        return openai_tools
    
    async def _connect_sse(self) -> None:
        """Connect to MCP server via SSE."""
        # Implementation for SSE transport
        pass


# Global MCP client instance (lazy initialization)
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> Optional[MCPClient]:
    """Get or create MCP client instance."""
    global _mcp_client
    
    if not settings.MCP_ENABLED:
        return None
    
    if _mcp_client is None and settings.MCP_SERVER_COMMAND:
        import json
        
        args = []
        if settings.MCP_SERVER_ARGS:
            try:
                args = json.loads(settings.MCP_SERVER_ARGS)
            except json.JSONDecodeError:
                args = settings.MCP_SERVER_ARGS.split()
        
        _mcp_client = MCPClient(
            server_command=settings.MCP_SERVER_COMMAND,
            server_args=args,
            transport=settings.MCP_TRANSPORT,
            sse_endpoint=settings.MCP_SSE_ENDPOINT or None,
        )
    
    return _mcp_client


async def initialize_mcp() -> None:
    """Initialize MCP connection if enabled."""
    client = get_mcp_client()
    if client:
        await client.connect()


async def shutdown_mcp() -> None:
    """Shutdown MCP connection."""
    client = get_mcp_client()
    if client:
        await client.disconnect()
