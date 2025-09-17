import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    keyword_list = ['break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new', 'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'await', 'async']
    rules = [
        HighlightingRule(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|`[^`]*`', 'string'),
        HighlightingRule(r'//[^\n]*', 'comment'),
        HighlightingRule(r'/\*.*?\*/', 'comment'),
        HighlightingRule(r'\b(' + '|'.join(keyword_list) + r')\b', 'keyword'),
        HighlightingRule(r'\b\d+(?:\.\d+)?\b', 'number'),
    ]
    language_manager.register_language(
        name="JavaScript",
        extensions=[".js", ".jsx"],
        highlighter_class=BaseHighlighter,  # <-- ИСПРАВЛЕНО
        rules=rules
    )