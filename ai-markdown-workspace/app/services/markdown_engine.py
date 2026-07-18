"""
Markdown Engine Service for AI Markdown Workspace.
Converts Markdown to HTML with syntax highlighting using Pygments.
Supports GitHub Flavored Markdown (GFM).
"""
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name
from typing import Optional, Dict, Any, List
import re


class MarkdownEngine:
    """
    Markdown to HTML conversion engine with syntax highlighting.
    
    Features:
    - GitHub Flavored Markdown (tables, task lists, strikethrough)
    - Code syntax highlighting with Pygments
    - Table of Contents generation
    - Custom CSS class support
    """
    
    def __init__(
        self,
        extensions: Optional[List[str]] = None,
        style: str = 'monokai',
    ):
        """
        Initialize the Markdown engine.
        
        Args:
            extensions: List of markdown extensions to enable
            style: Pygments syntax highlighting style
        """
        self.extensions = extensions or [
            'extra',      # Tables, fenced code, definitions
            'codehilite', # Syntax highlighting
            'toc',        # Table of contents
            'fenced_code',# Fenced code blocks
            'tables',     # Markdown tables
            'nl2br',      # Newline to <br>
        ]
        self.style = style
        self._formatter = HtmlFormatter(
            style=style,
            cssclass='codehilite',
            linenos=False,
            wrapcode=True,
        )
    
    def render(self, text: str) -> str:
        """
        Render Markdown text to HTML.
        
        Args:
            text: Markdown content
            
        Returns:
            str: HTML string
        """
        md = markdown.Markdown(
            extensions=self.extensions,
            output_format='html5',
        )
        html = md.convert(text)
        return html
    
    def render_with_toc(self, text: str) -> tuple[str, str]:
        """
        Render Markdown with table of contents.
        
        Args:
            text: Markdown content
            
        Returns:
            tuple: (html_content, toc_html)
        """
        md = markdown.Markdown(
            extensions=self.extensions + ['toc'],
            output_format='html5',
            extension_configs={
                'toc': {
                    'permalink': True,
                    'permalink_class': 'header-anchor',
                    'baselevel': 2,
                }
            }
        )
        html = md.convert(text)
        toc = md.toc
        return html, toc
    
    def highlight_code(
        self,
        code: str,
        language: Optional[str] = None,
        show_line_numbers: bool = False,
    ) -> str:
        """
        Highlight code block with Pygments.
        
        Args:
            code: Source code to highlight
            language: Programming language name
            show_line_numbers: Whether to show line numbers
            
        Returns:
            str: Highlighted HTML
        """
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code)
        except Exception:
            lexer = get_lexer_by_name('text')
        
        formatter = HtmlFormatter(
            style=self.style,
            cssclass='codehilite',
            linenos='table' if show_line_numbers else False,
            wrapcode=True,
        )
        
        highlighted = highlight(code, lexer, formatter)
        return highlighted
    
    def extract_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract code blocks from Markdown text.
        
        Args:
            text: Markdown content
            
        Returns:
            list: List of dicts with 'language', 'code', 'filename' keys
        """
        code_blocks = []
        # Pattern: ```language filename\n code ```
        pattern = r'```(\w+)?(?:\s+([^\n]+))?\n(.*?)```'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            language = match.group(1) or 'text'
            filename = match.group(2).strip() if match.group(2) else ''
            code = match.group(3).strip()
            
            code_blocks.append({
                'index': len(code_blocks),
                'language': language,
                'filename': filename,
                'code': code,
            })
        
        return code_blocks
    
    def add_copy_buttons(self, html: str) -> str:
        """
        Add copy buttons to code blocks in HTML.
        
        Args:
            html: HTML content with code blocks
            
        Returns:
            str: HTML with copy buttons added
        """
        # Find all pre.codehilite blocks and add copy button
        pattern = r'(<pre class="codehilite">.*?</pre>)'
        
        def replace_block(match: re.Match) -> str:
            block = match.group(1)
            wrapper = f'''
            <div class="relative code-block-wrapper">
                <button class="copy-code-btn absolute top-2 right-2 bg-gray-700 hover:bg-gray-600 text-white text-xs px-2 py-1 rounded"
                        onclick="copyCodeBlock(this)">
                    📋 Copy
                </button>
                {block}
            </div>
            '''
            return wrapper
        
        return re.sub(pattern, replace_block, html, flags=re.DOTALL)
    
    def render_full(self, text: str, with_toc: bool = False) -> Dict[str, Any]:
        """
        Full rendering with all features.
        
        Args:
            text: Markdown content
            with_toc: Whether to generate table of contents
            
        Returns:
            dict: Rendering results with html, toc, code_blocks
        """
        result = {
            'html': '',
            'toc': '',
            'code_blocks': [],
        }
        
        # Extract code blocks before rendering
        result['code_blocks'] = self.extract_code_blocks(text)
        
        # Render Markdown
        if with_toc:
            html, toc = self.render_with_toc(text)
            result['toc'] = toc
        else:
            html = self.render(text)
        
        # Add copy buttons to code blocks
        result['html'] = self.add_copy_buttons(html)
        
        return result


# Global instance
markdown_engine = MarkdownEngine()


def get_markdown_engine() -> MarkdownEngine:
    """Dependency function to get markdown engine instance."""
    return markdown_engine


def render_markdown(text: str) -> str:
    """Convenience function to render markdown."""
    return markdown_engine.render(text)
