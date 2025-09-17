import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    rules = [
        HighlightingRule(r'//[^\n]*', "comment"),
        HighlightingRule(r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/', "comment"),
        HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', "string"),
        HighlightingRule(r'\b(fn|let|mut|if|else|while|for|in|loop|match|return|pub|use|mod|struct|enum|impl|trait|const|static|true|false|self)\b', "keyword"),
        HighlightingRule(r'\'[a-zA-Z]\'', "string"),
        HighlightingRule(r'\b[0-9]+(_[0-9]+)*(\.[0-9]+)?\b', "number"),
        HighlightingRule(r'![a-zA-Z_]+', "decorator"),
    ]
    language_manager.register_language(
        name="Rust", extensions=[".rs"], highlighter_class=BaseHighlighter, rules=rules
    )