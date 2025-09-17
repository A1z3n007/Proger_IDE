# plugins/syntax_highlighter.py
import re
from collections import namedtuple
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

HighlightingRule = namedtuple("HighlightingRule", ["pattern", "format_key"])

class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, rules, scheme):
        super().__init__(parent)
        self.rules = []
        # scheme может быть str (#RRGGBB) — конвертим в QColor
        _scheme = {k: (v if isinstance(v, QColor) else QColor(v)) for k, v in scheme.items()}
        for rule in rules:
            fmt = QTextCharFormat()
            color = _scheme.get(rule.format_key)
            if color:
                fmt.setForeground(color)
                if rule.format_key in ("keyword", "self"):
                    fmt.setFontWeight(QFont.Bold)
                if rule.format_key == "comment":
                    fmt.setFontItalic(True)
            # в плагинах pattern уже re.compile — используем как есть
            self.rules.append((rule.pattern if hasattr(rule.pattern, "finditer") else re.compile(rule.pattern), fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
