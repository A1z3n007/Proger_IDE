import re
from main import BaseHighlighter, HighlightingRule

def register(language_manager):
    rules = [
        HighlightingRule(r'//[^\n]*', "comment"),
        HighlightingRule(r'#[^\n]*', "comment"),
        HighlightingRule(r'"[^"\\]*(\\.[^"\\]*)*"', "string"),
        HighlightingRule(r"'[^'\\]*(\\.[^'\\]*)*'", "string"),
        HighlightingRule(r'\b(echo|if|else|elseif|while|for|foreach|do|switch|case|break|continue|return|function|class|public|private|protected|static|new|use|namespace|const|define|true|false|null|__FILE__|__LINE__)\b', "keyword"),
        HighlightingRule(r'\$[a-zA-Z_][a-zA-Z0-9_]*', "decorator"),
        HighlightingRule(r'\b[0-9]+(\.[0-9]+)?\b', "number"),
    ]
    language_manager.register_language(
        name="PHP", extensions=[".php"], highlighter_class=BaseHighlighter, rules=rules
    )