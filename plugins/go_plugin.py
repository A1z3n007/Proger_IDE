import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    rules = [
        HighlightingRule(r'//[^\n]*', "comment"),
        HighlightingRule(r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/', "comment"),
        HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', "string"),
        HighlightingRule(r'`[^`]*`', "string"),
        HighlightingRule(r'\b(break|case|chan|const|continue|default|defer|else|fallthrough|for|func|go|goto|if|import|interface|map|package|range|return|select|struct|switch|type|var)\b', "keyword"),
        HighlightingRule(r'\b(true|false|nil|iota)\b', "keyword"),
        HighlightingRule(r'\b[0-9]+(\.[0-9]+)?\b', "number"),
    ]
    language_manager.register_language(
        name="Go", extensions=[".go"], highlighter_class=BaseHighlighter, rules=rules
    )