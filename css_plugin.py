import re
from collections import namedtuple
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

HighlightingRule = namedtuple("HighlightingRule", ["pattern", "format_key"])

class CSSHighlighter(QSyntaxHighlighter):

    def __init__(self, document, rules, scheme):
        super().__init__(document)
        self._rules = []
        self._scheme = scheme
        for rule in rules:
            fmt = QTextCharFormat()
            colour = scheme.get(rule.format_key)
            if colour:
                if not isinstance(colour, QColor):
                    colour = QColor(colour) 
                fmt.setForeground(colour)
                if rule.format_key == "keyword":
                    fmt.setFontWeight(QFont.Bold)
            self._rules.append((rule.pattern, fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
        self.setCurrentBlockState(0)

def register(language_manager):
    rules = []
    rules.append(HighlightingRule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''), 'string'))
    rules.append(HighlightingRule(re.compile(r'/\*.*?\*/', re.DOTALL), 'comment'))
    rules.append(HighlightingRule(re.compile(r'\b[a-zA-Z\-]+(?=\s*:)'), 'keyword'))
    rules.append(HighlightingRule(re.compile(r'\b\d+(?:\.\d+)?(?:px|em|rem|%|s|ms)?\b'), 'number'))
    rules.append(HighlightingRule(re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b'), 'number'))
    language_manager.register_language('CSS', ['.css'], CSSHighlighter, rules)