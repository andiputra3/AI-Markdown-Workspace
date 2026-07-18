"""
Prompt Builder Service for AI Markdown Workspace.
Manages slash command templates and prompt generation.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime


class PromptBuilder:
    """
    Manages builder templates and generates prompts for slash commands.
    
    Builders are specialized prompt templates that generate specific outputs:
    - /spec-builder → SPECIFICATION.md
    - /plan-builder → BUILD_PLAN.md
    - /sqlite-builder → schema.sql
    - etc.
    """
    
    def __init__(self):
        # Default templates (also seeded in DB)
        self.default_templates = {
            '/spec-builder': {
                'name': 'Specification Builder',
                'description': 'Generate SPECIFICATION.md for a project',
                'prompt_template': '''Create a comprehensive SPECIFICATION.md for project "{project_name}". Include:

1. **Project Overview**
   - Problem statement
   - Goals and objectives
   - Target users

2. **Features**
   - Core features (must-have)
   - Nice-to-have features
   - Future considerations

3. **Tech Stack**
   - Backend framework
   - Frontend framework
   - Database
   - External services

4. **Database Schema**
   - Table definitions
   - Relationships
   - Indexes

5. **API Endpoints**
   - REST endpoints
   - Request/response formats

6. **File Structure**
   - Project organization
   - Key directories

7. **Milestones**
   - Phase 1: MVP
   - Phase 2: Core features
   - Phase 3: Polish

Output clean Markdown with proper headings and code blocks.''',
                'output_filename': 'SPECIFICATION.md',
            },
            '/plan-builder': {
                'name': 'Planning Builder',
                'description': 'Generate BUILD_PLAN.md',
                'prompt_template': '''Create a detailed BUILD_PLAN.md for "{project_name}" based on its specification. Include:

## Phase Breakdown

### Phase 1: Foundation
- [ ] Task 1
- [ ] Task 2
- Dependencies: None
- Estimated time: X days
- Priority: High

### Phase 2: Core Implementation
- [ ] Task 1
- [ ] Task 2
- Dependencies: Phase 1
- Estimated time: X days
- Priority: High

### Phase 3: Testing & Polish
- [ ] Task 1
- [ ] Task 2
- Dependencies: Phase 2
- Estimated time: X days
- Priority: Medium

## Timeline
| Phase | Start | End | Status |
|-------|-------|-----|--------|
| 1 | TBD | TBD | Not started |
| 2 | TBD | TBD | Not started |
| 3 | TBD | TBD | Not started |

## Risk Assessment
- Technical risks
- Resource constraints
- Mitigation strategies''',
                'output_filename': 'BUILD_PLAN.md',
            },
            '/sqlite-builder': {
                'name': 'SQLite Builder',
                'description': 'Generate schema.sql',
                'prompt_template': '''Design complete SQLite schema for "{project_name}". Include:

```sql
-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ========== TABLES ==========
-- Create all tables with proper constraints

-- ========== INDEXES ==========
-- Performance indexes

-- ========== TRIGGERS ==========
-- Auto-update timestamps, audit logs

-- ========== SEED DATA ==========
-- Initial data for development
```

Requirements:
- Use INTEGER PRIMARY KEY AUTOINCREMENT for IDs
- Foreign keys with ON DELETE CASCADE
- created_at/updated_at timestamps (TEXT ISO 8601)
- Appropriate indexes for queries
- Check constraints where applicable

Output as single SQL code block.''',
                'output_filename': 'schema.sql',
            },
            '/api-builder': {
                'name': 'API Builder',
                'description': 'Generate API.md',
                'prompt_template': '''Design REST API for "{project_name}". Include:

## Authentication
- Method (JWT, Session, API Key)
- Endpoints: /login, /logout, /refresh

## Endpoints

### GET /resource
- Description: List resources
- Query params: page, limit, sort
- Response: 200 OK
```json
{
  "data": [],
  "pagination": {}
}
```

### POST /resource
- Description: Create resource
- Body:
```json
{
  "field1": "value",
  "field2": "value"
}
```
- Response: 201 Created

### GET /resource/{id}
- Description: Get single resource
- Response: 200 OK

### PUT /resource/{id}
- Description: Update resource
- Response: 200 OK

### DELETE /resource/{id}
- Description: Delete resource
- Response: 204 No Content

## Error Responses
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 500 Internal Server Error

Output as Markdown tables + JSON examples.''',
                'output_filename': 'API.md',
            },
            '/doc-builder': {
                'name': 'Documentation Builder',
                'description': 'Generate README.md',
                'prompt_template': '''Create README.md + DOCUMENTATION.md for "{project_name}". Include:

# README.md

## Project Name
Brief description (1-2 sentences)

## Features
- Feature 1
- Feature 2
- Feature 3

## Installation
```bash
git clone <repo>
cd <project>
pip install -r requirements.txt
```

## Usage
```bash
python main.py
```

## Configuration
Copy `.env.example` to `.env` and configure:
- `DATABASE_URL`
- `API_KEY`
- etc.

## Development
```bash
# Run tests
pytest

# Lint
flake8 .

# Type check
mypy .
```

## License
MIT

---

# DOCUMENTATION.md

## Architecture
High-level overview

## API Reference
Detailed endpoint docs

## Database Schema
ERD or table descriptions

## Contributing
Guidelines for contributors

Output both files as separate sections.''',
                'output_filename': 'README.md',
            },
            '/roadmap-builder': {
                'name': 'Roadmap Builder',
                'description': 'Generate ROADMAP.md',
                'prompt_template': '''Create ROADMAP.md for "{project_name}" with:

# Product Roadmap

## Vision
Long-term vision for the product

## Version Milestones

### v1.0 - MVP (Q1 2025)
**Theme:** Core functionality
- [ ] Feature A
- [ ] Feature B
- [ ] Feature C

### v2.0 - Growth (Q2 2025)
**Theme:** Scale and performance
- [ ] Feature D
- [ ] Feature E
- [ ] Optimization F

### v3.0 - Enterprise (Q3 2025)
**Theme:** Advanced features
- [ ] SSO integration
- [ ] Audit logging
- [ ] Advanced analytics

## Breaking Changes
Planned breaking changes by version

## Future Considerations
- AI-powered features
- Mobile app
- Plugin system

## Timeline Visualization
```
Q1 2025: [====v1.0====]
Q2 2025:          [====v2.0====]
Q3 2025:                    [====v3.0====]
```

Output as clean Markdown.''',
                'output_filename': 'ROADMAP.md',
            },
            '/audit-file': {
                'name': 'File Audit',
                'description': 'Audit history of a specific file',
                'prompt_template': '''Analyze the file creation log for "{file_path}" in workspace "{workspace_name}". Provide:

## File Audit Report: {file_path}

### Creation Summary
- **Created:** {created_date}
- **Created by:** {source_type}
- **Initial size:** {initial_size} bytes

### Timeline of Operations
| Date | Action | Source | Details |
|------|--------|--------|---------|
| ... | ... | ... | ... |

### Edit Frequency
- Total edits: {edit_count}
- Average edits per day: {avg_edits}
- Most active period: {period}

### Size Growth
- Initial: {initial_size} bytes
- Current: {current_size} bytes
- Growth: {growth_percentage}%

### Contributors (Sources)
| Source | Operations | Percentage |
|--------|------------|------------|
| Chat messages | X | Y% |
| Builders | X | Y% |
| Manual | X | Y% |

### Recommendations
Based on the audit history...

Output as formatted Markdown report.''',
                'output_filename': None,
            },
        }
    
    def get_template(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Get template for a slash command.
        
        Args:
            command: Slash command (e.g., '/spec-builder')
            
        Returns:
            dict: Template info or None
        """
        return self.default_templates.get(command)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [
            {
                'command': cmd,
                'name': info['name'],
                'description': info['description'],
                'output_filename': info['output_filename'],
            }
            for cmd, info in self.default_templates.items()
        ]
    
    def build_prompt(
        self,
        command: str,
        project_name: str = "",
        file_path: str = "",
        workspace_name: str = "",
        **kwargs
    ) -> str:
        """
        Build prompt from template with variables.
        
        Args:
            command: Slash command
            project_name: Project name variable
            file_path: File path variable
            workspace_name: Workspace name variable
            **kwargs: Additional variables
            
        Returns:
            str: Rendered prompt
        """
        template = self.get_template(command)
        if not template:
            raise ValueError(f"Unknown command: {command}")
        
        prompt = template['prompt_template']
        
        # Replace variables
        replacements = {
            '{project_name}': project_name,
            '{file_path}': file_path,
            '{workspace_name}': workspace_name,
            **kwargs
        }
        
        for key, value in replacements.items():
            prompt = prompt.replace(key, value)
        
        return prompt
    
    def get_output_filename(self, command: str) -> Optional[str]:
        """Get default output filename for command."""
        template = self.get_template(command)
        return template['output_filename'] if template else None


# Global instance
prompt_builder = PromptBuilder()


def get_prompt_builder() -> PromptBuilder:
    """Dependency function to get prompt builder instance."""
    return prompt_builder
