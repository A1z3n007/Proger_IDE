import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    rules = [
        HighlightingRule(r'#[^\n]*', "comment"),
        HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', "string"),
        HighlightingRule(r"'[^'\\]*(\\.[^'\\]*)*'", "string"),
        HighlightingRule(r'\b(def|end|if|else|elsif|while|for|in|do|class|module|begin|rescue|ensure|return|yield|case|when|then|true|false|nil|self)\b', "keyword"),
        HighlightingRule(r':[a-zA-Z_][a-zA-Z0-9_]*', "string"),
        HighlightingRule(r'\b[0-9]+(\.[0-9]+)?\b', "number"),
        HighlightingRule(r'@[a-zA-Z_][a-zA-Z0-9_]*', "decorator"),
    ]
    language_manager.register_language(
        name="Ruby", extensions=[".rb"], highlighter_class=BaseHighlighter, rules=rules
    )