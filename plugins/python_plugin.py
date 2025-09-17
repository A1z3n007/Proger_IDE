import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    rules = [
        HighlightingRule(r'\b(and|as|assert|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|True|False|None|self)\b', "keyword"),
        HighlightingRule(r'@[A-Za-z0-9_]+', "decorator"),
        HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', "string"),
        HighlightingRule(r"'[^'\\]*(\\.[^'\\]*)*'", "string"),
        HighlightingRule(r'#[^\n]*', "comment"),
        HighlightingRule(r'\b[0-9]+\b', "number"),
    ]
    language_manager.register_language(
        name="Python",
        extensions=[".py", ".pyw"],
        highlighter_class=BaseHighlighter,  # <-- ИСПРАВЛЕНО
        rules=rules
    )