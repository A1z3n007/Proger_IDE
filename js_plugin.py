import re
from collections import namedtuple
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

HighlightingRule = namedtuple("HighlightingRule", ["pattern", "format_key"])

class JSHighlighter(QSyntaxHighlighter):
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
                if rule.format_key == 'keyword':
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
    rules.append(HighlightingRule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|`[^`]*`'), 'string'))
    rules.append(HighlightingRule(re.compile(r'//.*'), 'comment'))
    rules.append(HighlightingRule(re.compile(r'/\*.*?\*/', re.DOTALL), 'comment'))
    keyword_list = [
        'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
        'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function',
        'if', 'import', 'in', 'instanceof', 'let', 'new', 'return', 'super',
        'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with',
        'yield', 'await', 'async'
    ]
    keyword_pattern = r'\b(?:' + '|'.join(keyword_list) + r')\b'
    rules.append(HighlightingRule(re.compile(keyword_pattern), 'keyword'))
    rules.append(HighlightingRule(re.compile(r'\b\d+(?:\.\d+)?\b'), 'number'))
    language_manager.register_language('JavaScript', ['.js', '.jsx', '.mjs'], JSHighlighter, rules)