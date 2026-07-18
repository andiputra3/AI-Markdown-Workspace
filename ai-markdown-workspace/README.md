# AI Markdown Workspace (HTMX Edition)

AI-powered Markdown workspace with HTMX + Tailwind CSS, featuring full audit logging for file operations.

## Features

- 💬 **Chat Interface** - Real-time AI chat with streaming responses
- 📁 **File Manager** - Create, edit, delete files with full audit trail
- 🔍 **Audit Log** - Complete history of all file operations
- 🗄️ **SQLite Viewer** - Browse and query databases
- ⚙️ **Settings** - Configure AI backend, markdown, and more
- 🧠 **Builder Commands** - Slash commands for generating specifications, plans, etc.
- 🕐 **WIB Timezone** - All timestamps displayed in Western Indonesian Time (UTC+7)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Database**: SQLite with aiosqlite
- **Markdown**: Python-Markdown + Pygments
- **AI**: OpenAI-compatible API (Ollama, vLLM, MiMo, etc.)

## Quick Start

### 1. Install Dependencies

```bash
cd ai-markdown-workspace
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your AI backend settings
```

### 3. Run the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open in Browser

Navigate to `http://localhost:8000`

## Project Structure

```
ai-markdown-workspace/
├── app/
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database schema & connection
│   ├── main.py             # FastAPI application entry
│   ├── models/             # Pydantic models
│   ├── routers/
│   │   ├── chat.py         # Chat endpoints
│   │   ├── files.py        # File manager endpoints
│   │   ├── audit.py        # Audit log endpoints
│   │   ├── sqlite_viewer.py
│   │   ├── settings.py
│   │   ├── builders.py
│   │   ├── rag.py
│   │   ├── workspaces.py
│   │   └── export.py
│   ├── services/
│   │   ├── ai_client.py    # AI API client
│   │   ├── audit_log.py    # File audit service
│   │   ├── file_manager.py # File operations
│   │   ├── markdown_engine.py
│   │   └── timezone_service.py
│   └── utils/
├── templates/
│   ├── base.html           # Base layout
│   ├── pages/
│   │   └── chat.html       # Chat page
│   ├── components/
│   │   ├── sidebar.html
│   │   ├── topbar.html
│   │   ├── chat_message_user.html
│   │   ├── chat_message_ai.html
│   │   └── prompt_input.html
│   └── partials/
├── static/
│   ├── css/
│   │   └── markdown.css    # Markdown styles
│   ├── js/
│   └── img/
├── workspaces/             # User workspaces
├── data/                   # SQLite database
├── requirements.txt
├── .env.example
└── README.md
```

## Key Features

### Chat with Edit & Copy
- ✏️ Edit any user message (with history tracking)
- 📋 Copy sent messages or AI replies
- 🔄 Regenerate AI responses
- 📁 Generate files from code blocks

### File Audit Trail
Every file operation is logged:
- Create, Edit, Delete, Rename
- Source tracking (chat message, builder, manual)
- Diff summaries for edits
- Size and line count tracking

### WIB Timestamps
All timestamps are stored as UTC but displayed in WIB (Asia/Jakarta, UTC+7).

### Builder Commands
Type `/` in the chat input to access builders:
- `/spec-builder` - Generate SPECIFICATION.md
- `/plan-builder` - Generate BUILD_PLAN.md
- `/sqlite-builder` - Generate schema.sql
- `/api-builder` - Generate API.md
- `/doc-builder` - Generate documentation
- `/roadmap-builder` - Generate ROADMAP.md
- `/audit-file` - Audit file history

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Redirect to /chat |
| GET | `/chat` | Chat page |
| POST | `/chat/send` | Send message |
| GET | `/chat/stream` | SSE streaming |
| GET | `/files` | File manager |
| GET | `/audit` | Audit dashboard |
| GET | `/sqlite` | SQLite viewer |
| GET | `/settings` | Settings page |

## Development Phases

- ✅ **Phase 1**: Foundation (config, database, services, templates)
- ✅ **Phase 2**: Chat Core (send, edit, copy, regenerate)
- 🔄 **Phase 3**: File System + Audit (in progress)
- ⏳ **Phase 4**: SQLite + Settings
- ⏳ **Phase 5**: Builders & RAG
- ⏳ **Phase 6**: Polish & Deployment

## License

MIT License
