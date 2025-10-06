import sys, os, re, types, json, shutil, urllib.request
from collections import namedtuple

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QMessageBox, QToolBar,
    QWidget, QTabWidget, QTreeView, QFileSystemModel, QDockWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPlainTextEdit, QActionGroup,
    QTextEdit, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QVBoxLayout,
    QDialog, QListWidget, QListWidgetItem, QLabel, QFileIconProvider, QMenu, QInputDialog
)
from PyQt5.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextDocument, QTextCursor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QDir, QSettings, QRect, QSize, QProcess, QFileInfo

try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.inprocess import QtInProcessKernelManager
except ImportError:
    print("Ошибка: qtconsole не найден. Установите его: pip install -r requirements.txt")
    sys.exit(1)

class LanguageIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.language_colors = {}
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, 'languages.json')
            with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
            lang_map = {
                'python': ['.py', '.pyw'], 'javascript': ['.js', '.jsx', '.mjs'], 'html': ['.html', '.htm'],
                'css': ['.css'], 'c++': ['.cpp', '.h', '.cxx', '.hpp'], 'ruby': ['.rb'],
                'go': ['.go'], 'rust': ['.rs'], 'php': ['.php']
            }
            for lang, details in data.items():
                exts = lang_map.get(lang.lower(), [])
                for ext in exts: self.language_colors[ext] = QColor(details['color'])
        except Exception as e: print(f"Не удалось загрузить colors.json: {e}")

    def icon(self, fileInfo):
        if fileInfo.isFile():
            ext = f".{fileInfo.suffix().lower()}"
            if ext in self.language_colors:
                pixmap = QPixmap(16, 16); pixmap.fill(self.language_colors[ext]); return QIcon(pixmap)
        return super().icon(fileInfo)

HighlightingRule = namedtuple("HighlightingRule", ["pattern", "format_key"])
class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, rules, scheme):
        super().__init__(parent); self.rules = []; self.scheme = {key: QColor(value) for key, value in scheme.items()}
        for rule in rules:
            fmt = QTextCharFormat()
            if color := self.scheme.get(rule.format_key):
                fmt.setForeground(color)
                if rule.format_key in ["keyword", "self"]: fmt.setFontWeight(QFont.Bold)
                if rule.format_key == "comment": fmt.setFontItalic(True)
            pattern = re.compile(rule.pattern) if isinstance(rule.pattern, str) else rule.pattern
            self.rules.append((pattern, fmt))
    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text): self.setFormat(match.start(), match.end() - match.start(), fmt)

class LanguageManager:
    def __init__(self):
        self.languages = {}; self.plugin_dir = 'plugins'
        if not os.path.exists(self.plugin_dir): os.makedirs(self.plugin_dir)
        if self.plugin_dir not in sys.path: sys.path.insert(0, self.plugin_dir)
        self.load_plugins()
    def load_plugins(self):
        self.languages = {}
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('_plugin.py') and filename != '__init__.py':
                try:
                    module_name = filename[:-3]
                    if module_name in sys.modules:
                        import importlib; module = importlib.reload(sys.modules[module_name])
                    else: module = __import__(module_name)
                    if hasattr(module, 'register'): module.register(self); print(f"Плагин '{filename}' успешно загружен.")
                except Exception as e: print(f"Не удалось загрузить плагин {filename}: {e}")
    def register_language(self, name, extensions, highlighter_class, rules):
        for ext in extensions: self.languages[ext.lower()] = {'highlighter': highlighter_class, 'rules': rules, 'name': name}
    def get_language_by_extension(self, ext): return self.languages.get(ext.lower())

class LineNumberArea(QWidget):
    def __init__(self, editor): super().__init__(editor); self.code_editor = editor
    def sizeHint(self): return QSize(self.code_editor.lineNumberAreaWidth(), 0)
    def paintEvent(self, event): self.code_editor.lineNumberAreaPaintEvent(event)

class EditorWidget(QPlainTextEdit):
    def __init__(self, main_window):
        super().__init__(main_window); self.main_window = main_window
        self.file_path = None; self.is_modified = False; self.highlighter = None
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.textChanged.connect(self.on_text_changed)
        self.setFont(QFont('Consolas', 12)); self.updateLineNumberAreaWidth(0)
    def keyPressEvent(self, event):
        pair_map = {'(': ')', '{': '}', '[': ']', '"': '"', "'": "'"}
        key_text = event.text()
        if key_text in pair_map:
            super().keyPressEvent(event); self.insertPlainText(pair_map[key_text]); self.moveCursor(QTextCursor.Left); return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor(); current_line_text = cursor.block().text()
            indentation = re.match(r'^\s*', current_line_text).group(0)
            super().keyPressEvent(event); self.insertPlainText(indentation)
            if current_line_text.strip().endswith((':', '{', '(', '[')): self.insertPlainText("    ")
            return
        super().keyPressEvent(event)
    def on_text_changed(self):
        if not self.is_modified: self.is_modified = True; self.main_window.update_tab_title(self)
    def set_highlighter(self, highlighter_class, rules, scheme): self.highlighter = highlighter_class(self.document(), rules, scheme)
    def lineNumberAreaWidth(self): return 10 + self.fontMetrics().horizontalAdvance('9') * len(str(max(1, self.blockCount())))
    def updateLineNumberAreaWidth(self, _=None): self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    def updateLineNumberArea(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
    def resizeEvent(self, event):
        super().resizeEvent(event); cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area); theme = self.main_window.themes[self.main_window.current_theme_name]
        painter.fillRect(event.rect(), QColor(theme['ui']['background'])); block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible():
                painter.setPen(QColor(theme['syntax']['comment']))
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(), Qt.AlignRight, str(block.blockNumber() + 1))
            block = block.next(); top += self.blockBoundingRect(block).height()
    def highlightCurrentLine(self):
        selection = QTextEdit.ExtraSelection(); theme = self.main_window.themes[self.main_window.current_theme_name]
        selection.format.setBackground(QColor(theme['ui']['highlight']))
        selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor(); selection.cursor.clearSelection(); self.setExtraSelections([selection])

class VariableExplorer(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Переменная', 'Тип', 'Значение'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.setEditTriggers(QTableWidget.NoEditTriggers)
    def update_variables(self, kernel_manager):
        if not (kernel_manager and kernel_manager.kernel): return
        shell = kernel_manager.kernel.shell; variables = shell.user_ns; self.setRowCount(0)
        user_vars = {n: v for n, v in variables.items() if not n.startswith('_') and not isinstance(v, (types.ModuleType, types.FunctionType))}
        self.setRowCount(len(user_vars))
        for i, (name, value) in enumerate(user_vars.items()):
            self.setItem(i, 0, QTableWidgetItem(name)); self.setItem(i, 1, QTableWidgetItem(type(value).__name__)); self.setItem(i, 2, QTableWidgetItem(repr(value)[:200]))

class PluginManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Менеджер плагинов")
        self.resize(600, 400)

        self.layout = QVBoxLayout(self)
        self.plugin_list = QListWidget()
        self.plugin_list.setStyleSheet("""
            QListWidget::item {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 10px;
                margin: 5px;
            }
            QListWidget::item:hover {
                background-color: #2A2A2A;
            }
        """)
        self.layout.addWidget(self.plugin_list)
        self.load_plugins_from_catalog()

    def load_plugins_from_catalog(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            catalog_path = os.path.join(script_dir, 'plugins_catalog.json')
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.catalog = json.load(f)

            self.installed_plugins = [f for f in os.listdir('plugins') if f.endswith('_plugin.py')]
            self.plugin_list.clear()

            for plugin_data in self.catalog:
                item_widget = self.create_plugin_item(plugin_data)
                list_item = QListWidgetItem()
                list_item.setSizeHint(item_widget.sizeHint())
                self.plugin_list.addItem(list_item)
                self.plugin_list.setItemWidget(list_item, item_widget)

        except FileNotFoundError:
            self.plugin_list.addItem("Ошибка: файл 'plugins_catalog.json' не найден.")
        except Exception as e:
            self.plugin_list.addItem(f"Ошибка загрузки каталога: {e}")

    def create_plugin_item(self, plugin_data):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(f"<b>{plugin_data['name']}</b> <small style='color: #888;'>v{plugin_data['version']}</small>")
        author_label = QLabel(f"<small style='color: #aaa;'>Автор: {plugin_data['author']}</small>")
        description_label = QLabel(plugin_data['description'])
        description_label.setWordWrap(True)

        text_layout.addWidget(name_label)
        text_layout.addWidget(author_label)
        text_layout.addWidget(description_label)
        text_layout.addStretch()

        main_layout.addLayout(text_layout, 1)

        plugin_filename = plugin_data['filename']
        if plugin_filename in self.installed_plugins:
            btn = QPushButton("Удалить")
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda: self.uninstall_plugin(plugin_filename))
        else:
            btn = QPushButton("Установить")
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda: self.install_plugin(plugin_data['url'], plugin_filename))

        main_layout.addWidget(btn, 0, Qt.AlignVCenter)
        return widget

    def install_plugin(self, url, filename):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ProgerIDE/1.0'})
            with urllib.request.urlopen(req) as response: content = response.read()
            with open(os.path.join('plugins', filename), 'wb') as f: f.write(content)
            QMessageBox.information(self, "Успех", f"Плагин '{filename}' установлен. Перезапустите IDE.")
            self.load_plugins_from_catalog()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить плагин:\n{e}")

    def uninstall_plugin(self, filename):
        try:
            os.remove(os.path.join('plugins', filename))
            QMessageBox.information(self, "Успех", f"Плагин '{filename}' удален. Перезапустите IDE.")
            self.load_plugins_from_catalog()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить плагин: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.settings = QSettings('ProgerIDE', 'Editor')
        self.current_theme_name = self.settings.value('theme', 'vscode_dark')
        self.language_manager = LanguageManager()
        self.initUI(); self.start_kernel(); self.set_theme(self.current_theme_name)

    def initUI(self):
        self.setWindowTitle('Proger IDE'); self.resize(1800, 1200)
        self.themes = {
            "vscode_dark": {"ui": {"background": "#1E1E1E", "foreground": "#D4D4D4", "highlight": "#2A2A2A", "border": "#3C3C3C"}, "syntax": {"normal": "#D4D4D4", "comment": "#6A9955", "string": "#CE9178", "number": "#B5CEA8", "keyword": "#C586C0", "class": "#4EC9B0", "function": "#DCDCAA", "decorator": "#C586C0"}},
            "monokai": {"ui": {"background": "#272822", "foreground": "#F8F8F2", "highlight": "#3E3D32", "border": "#3E3D32"}, "syntax": {"normal": "#F8F8F2", "comment": "#75715E", "string": "#E6DB74", "number": "#AE81FF", "keyword": "#F92672", "class": "#A6E22E", "function": "#A6E22E", "decorator": "#66D9EF"}},
            "dracula": {"ui": {"background": "#282a36", "foreground": "#f8f8f2", "highlight": "#44475a", "border": "#6272a4"}, "syntax": {"normal": "#f8f8f2", "comment": "#6272a4", "string": "#f1fa8c", "number": "#bd93f9", "keyword": "#ff79c6", "class": "#8be9fd", "function": "#50fa7b", "decorator": "#ffb86c"}},
            "nord": {"ui": {"background": "#2e3440", "foreground": "#d8dee9", "highlight": "#3b4252", "border": "#4c566a"}, "syntax": {"normal": "#d8dee9", "comment": "#4c566a", "string": "#a3be8c", "number": "#b48ead", "keyword": "#81a1c1", "class": "#8fbcbb", "function": "#88c0d0", "decorator": "#ebcb8b"}},
            "one_dark": {"ui": {"background": "#282c34", "foreground": "#abb2bf", "highlight": "#2c313a", "border": "#3a3f4b"}, "syntax": {"normal": "#abb2bf", "comment": "#5c6370", "string": "#98c379", "number": "#d19a66", "keyword": "#c678dd", "class": "#e5c07b", "function": "#61afef", "decorator": "#e06c75"}},
            "solarized_light": {"ui": {"background": "#fdf6e3", "foreground": "#657b83", "highlight": "#eee8d5", "border": "#93a1a1"}, "syntax": {"normal": "#657b83", "comment": "#93a1a1", "string": "#2aa198", "number": "#d33682", "keyword": "#859900", "class": "#b58900", "function": "#268bd2", "decorator": "#cb4b16"}},
        }
        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.find_widget = self.create_find_widget()
        editor_container = QWidget(); editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0,0,0,0); editor_layout.setSpacing(0)
        editor_layout.addWidget(self.tabs); editor_layout.addWidget(self.find_widget)
        self.setCentralWidget(editor_container)
        self.setup_docks(); self.setup_actions_and_menu(); self.new_file(); self.show()

    def create_find_widget(self):
        find_widget = QWidget(); find_widget.setVisible(False); layout = QHBoxLayout(find_widget); layout.setContentsMargins(5, 5, 5, 5)
        self.find_input = QLineEdit(placeholderText="Найти..."); self.replace_input = QLineEdit(placeholderText="Заменить...")
        self.case_checkbox = QCheckBox("Учитывать регистр")
        find_btn = QPushButton("Найти"); replace_btn = QPushButton("Заменить"); replace_all_btn = QPushButton("Заменить все")
        find_btn.clicked.connect(self.find_text); replace_btn.clicked.connect(self.replace_text)
        replace_all_btn.clicked.connect(self.replace_all_text); self.find_input.returnPressed.connect(self.find_text)
        layout.addWidget(self.find_input); layout.addWidget(self.case_checkbox); layout.addWidget(find_btn)
        layout.addWidget(self.replace_input); layout.addWidget(replace_btn); layout.addWidget(replace_all_btn)
        return find_widget

    def setup_docks(self):
        self.fs_model = QFileSystemModel(); self.fs_model.setRootPath(QDir.currentPath())
        icon_provider = LanguageIconProvider(); self.fs_model.setIconProvider(icon_provider)
        self.tree = QTreeView(); self.tree.setModel(self.fs_model); self.tree.setRootIndex(self.fs_model.index(QDir.currentPath()))
        self.tree.doubleClicked.connect(self.open_from_tree); self.tree.setHeaderHidden(True)
        for i in range(1, self.fs_model.columnCount()): self.tree.hideColumn(i)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        file_dock = QDockWidget("Проводник", self); file_dock.setWidget(self.tree); self.addDockWidget(Qt.LeftDockWidgetArea, file_dock)
        self.output_tabs = QTabWidget(); self.console = RichJupyterWidget(); self.variable_explorer = VariableExplorer(self)
        self.terminal_output = QPlainTextEdit(readOnly=True)
        self.output_tabs.addTab(self.console, "IPython Консоль"); self.output_tabs.addTab(self.terminal_output, "Терминал")
        output_dock = QDockWidget("Вывод", self); output_dock.setWidget(self.output_tabs); self.addDockWidget(Qt.BottomDockWidgetArea, output_dock)
        var_explorer_dock = QDockWidget("Переменные", self); var_explorer_dock.setWidget(self.variable_explorer)
        self.addDockWidget(Qt.RightDockWidgetArea, var_explorer_dock)

    def show_tree_context_menu(self, position):
        index = self.tree.indexAt(position)
        if not index.isValid(): return
        path = self.fs_model.filePath(index)
        menu = QMenu(); menu.addAction("Новый файл...", lambda: self.create_new_item(path, is_file=True))
        menu.addAction("Новая папка...", lambda: self.create_new_item(path, is_file=False))
        menu.addSeparator(); menu.addAction("Переименовать", lambda: self.rename_item(path))
        menu.addAction("Удалить", lambda: self.delete_item(path))
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def create_new_item(self, path, is_file):
        base_path = path if self.fs_model.isDir(self.fs_model.index(path)) else os.path.dirname(path)
        item_type = "файл" if is_file else "папку"
        name, ok = QInputDialog.getText(self, f"Создать {item_type}", f"Введите имя:")
        if ok and name:
            new_path = os.path.join(base_path, name)
            try:
                if is_file:
                    with open(new_path, 'w') as f: f.write('')
                    self.open_file(new_path)
                else: os.mkdir(new_path)
            except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось создать {item_type}:\n{e}")

    def rename_item(self, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try: os.rename(path, new_path)
            except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать:\n{e}")

    def delete_item(self, path):
        item_type = "папку" if os.path.isdir(path) else "файл"
        reply = QMessageBox.question(self, "Удаление", f"Вы уверены, что хотите удалить {item_type} '{os.path.basename(path)}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось удалить:\n{e}")

    def start_kernel(self):
        self.kernel_manager = QtInProcessKernelManager(); self.kernel_manager.start_kernel(show_banner=False)
        self.kernel_client = self.kernel_manager.client(); self.console.kernel_manager = self.kernel_manager
        self.console.kernel_client = self.kernel_client; self.console.executed.connect(lambda: self.variable_explorer.update_variables(self.kernel_manager))

    def setup_actions_and_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&Файл'); actions = [('Новый', 'Ctrl+N', self.new_file), ('Открыть', 'Ctrl+O', self.open_file_dialog), ('Сохранить', 'Ctrl+S', self.save_current_file), ('Сохранить как...', 'Ctrl+Shift+S', self.save_current_file_as), None, ('Запустить', 'F5', self.run_script), None, ('Выход', 'Ctrl+Q', self.close)]
        for item in actions:
            if item: action = QAction(item[0], self, shortcut=item[1], triggered=item[2]); file_menu.addAction(action)
            else: file_menu.addSeparator()
        edit_menu = menu_bar.addMenu('&Правка'); find_action = QAction("Найти/Заменить", self, shortcut="Ctrl+F", triggered=self.toggle_find_widget); edit_menu.addAction(find_action)
        view_menu = menu_bar.addMenu('&Вид'); theme_menu = view_menu.addMenu('Темы'); theme_group = QActionGroup(self)
        for theme_name in self.themes:
            action = QAction(theme_name, self, checkable=True, triggered=lambda c, n=theme_name: self.set_theme(n))
            if theme_name == self.current_theme_name: action.setChecked(True)
            theme_group.addAction(action); theme_menu.addAction(action)
        tools_menu = menu_bar.addMenu('&Инструменты'); plugin_action = QAction("Менеджер плагинов", self, triggered=self.open_plugin_manager); tools_menu.addAction(plugin_action)

    def open_plugin_manager(self): 
        dialog = PluginManagerDialog(self); 
        dialog.exec_()
    def toggle_find_widget(self): 
        self.find_widget.setVisible(not self.find_widget.isVisible());
    def find_text(self):
        editor = self.tabs.currentWidget();
        if not isinstance(editor, EditorWidget): return
        query = self.find_input.text(); flags = QTextDocument.FindFlags()
        if self.case_checkbox.isChecked(): flags |= QTextDocument.FindCaseSensitively
        if not editor.find(query, flags): editor.moveCursor(QTextDocument.Start); editor.find(query, flags)
    def replace_text(self):
        editor = self.tabs.currentWidget()
        if isinstance(editor, EditorWidget) and editor.textCursor().hasSelection(): editor.insertPlainText(self.replace_input.text()); self.find_text()
    def replace_all_text(self):
        editor = self.tabs.currentWidget();
        if not isinstance(editor, EditorWidget): return
        query = self.find_input.text(); replacement = self.replace_input.text()
        cursor = editor.textCursor(); editor.moveCursor(QTextDocument.Start); count = 0
        flags = QTextDocument.FindFlags()
        if self.case_checkbox.isChecked(): flags |= QTextDocument.FindCaseSensitively
        while editor.find(query, flags): editor.insertPlainText(replacement); count += 1
        editor.setTextCursor(cursor); QMessageBox.information(self, "Замена завершена", f"Выполнено замен: {count}")

    def set_theme(self, theme_name):
        if theme_name not in self.themes: return
        self.current_theme_name = theme_name; theme = self.themes[self.current_theme_name]
        stylesheet = f""" QMainWindow, QToolBar, QTreeView, QTabBar::tab, QStatusBar, QDockWidget, QLineEdit, QPushButton, QCheckBox, QListWidget, QMenu, QDialog, QTableCornerButton::section, QMenu::item {{ background-color: {theme['ui']['background']}; color: {theme['ui']['foreground']}; border: 1px solid {theme['ui']['border']}; }} QTextEdit, QPlainTextEdit, QTableWidget {{ background-color: {theme['ui']['background']}; color: {theme['ui']['foreground']}; border: 1px solid {theme['ui']['border']}; gridline-color: {theme['ui']['border']}; }} QHeaderView::section {{ background-color: {theme['ui']['highlight']}; color: {theme['ui']['foreground']}; border: 1px solid {theme['ui']['border']}; padding: 4px; }} RichJupyterWidget, #qtconsole_prompt_label {{ color: {theme['syntax']['normal']}; }} QDockWidget::title {{ background: {theme['ui']['highlight']}; border: none; padding: 4px; }} QTreeView::item:selected, QTabBar::tab:selected, QListWidget::item:selected, QMenu::item:selected {{ background-color: {theme['ui']['highlight']}; }} QTabWidget::pane {{ border: none; }} QPushButton {{ padding: 4px; }} """
        self.setStyleSheet(stylesheet); self.console.setStyleSheet(stylesheet)
        for i in range(self.tabs.count()):
            if isinstance(editor := self.tabs.widget(i), EditorWidget):
                self.apply_highlighter_to_editor(editor); editor.highlightCurrentLine()

    def new_file(self):
        editor = EditorWidget(self); 
        idx = self.tabs.addTab(editor, 'Безымянный');
        self.tabs.setCurrentIndex(idx); 
        self.set_theme(self.current_theme_name)
    def open_from_tree(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path): 
            self.open_file(path)
    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Открыть файл')
        if path: 
            self.open_file(path)
    def open_file(self, path):
        for i in range(self.tabs.count()):
            if getattr(self.tabs.widget(i), 'file_path', None) == path: 
                self.tabs.setCurrentIndex(i); 
                return
        try:
            with open(path, 'r', encoding='utf-8') as f: content = f.read()
            editor = EditorWidget(self); editor.setPlainText(content); editor.file_path = path
            self.apply_highlighter_to_editor(editor); idx = self.tabs.addTab(editor, os.path.basename(path))
            self.tabs.setCurrentIndex(idx); self.tabs.setTabToolTip(idx, path); self.set_theme(self.current_theme_name)
        except Exception as e: QMessageBox.critical(self, 'Ошибка', f'Не удалось открыть файл:\n{e}')
    def apply_highlighter_to_editor(self, editor):
        if not editor.file_path: return
        ext = os.path.splitext(editor.file_path)[1].lower()
        lang = self.language_manager.get_language_by_extension(ext)
        if lang: theme = self.themes[self.current_theme_name]; editor.set_highlighter(lang['highlighter'], lang['rules'], theme['syntax'])
    def save_current_file(self):
        if isinstance(editor := self.tabs.currentWidget(), EditorWidget): self.save_file(editor)
    def save_current_file_as(self):
        if isinstance(editor := self.tabs.currentWidget(), EditorWidget): self.save_file_as(editor)
    def save_file(self, editor):
        if not editor.file_path: return self.save_file_as(editor)
        try:
            with open(editor.file_path, 'w', encoding='utf-8') as f: f.write(editor.toPlainText())
            editor.is_modified = False; self.update_tab_title(editor); return True
        except Exception as e: QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить: {e}'); return False
    def save_file_as(self, editor):
        path, _ = QFileDialog.getSaveFileName(self, 'Сохранить как...');
        if not path: return False
        editor.file_path = path; self.update_tab_title(editor); self.apply_highlighter_to_editor(editor); return self.save_file(editor)
    def get_run_command(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        commands = {'.py': f'python "{file_path}"', '.js': f'node "{file_path}"', '.html': f'start "" "{file_path}"'}
        return commands.get(ext)
    def run_script(self):
        editor = self.tabs.currentWidget()
        if not (isinstance(editor, EditorWidget) and editor.file_path):
            QMessageBox.warning(self, "Внимание", "Сохраните файл перед запуском."); return
        if editor.is_modified and not self.save_file(editor): return
        command = self.get_run_command(os.path.abspath(editor.file_path))
        if not command:
            QMessageBox.warning(self, "Ошибка", f"Не знаю, как запустить файлы типа '{os.path.splitext(editor.file_path)[1]}'"); return
        self.output_tabs.setCurrentWidget(self.terminal_output); self.terminal_output.appendPlainText(f"> {command}\n")
        if not hasattr(self, 'terminal_process') or self.terminal_process.state() == QProcess.NotRunning:
            self.terminal_process = QProcess(self)
            self.terminal_process.readyReadStandardOutput.connect(lambda: self.terminal_output.appendPlainText(self.terminal_process.readAllStandardOutput().data().decode(errors='ignore')))
            self.terminal_process.readyReadStandardError.connect(lambda: self.terminal_output.appendPlainText(self.terminal_process.readAllStandardError().data().decode(errors='ignore')))
            shell = 'powershell.exe' if sys.platform == 'win32' else 'bash'
            self.terminal_process.start(shell)
        self.terminal_process.write(command.encode() + b'\n')
    def update_tab_title(self, editor):
        idx = self.tabs.indexOf(editor);
        if idx == -1: return
        title = os.path.basename(editor.file_path) if editor.file_path else "Безымянный"
        if editor.is_modified: title += "*";
        self.tabs.setTabText(idx, title)
    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor.is_modified:
            reply = QMessageBox.question(self, "Несохраненные изменения", f"В файле '{self.tabs.tabText(index)}' есть несохраненные изменения. Сохранить?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save and not self.save_file(editor): return
            elif reply == QMessageBox.Cancel: return
        self.tabs.removeTab(index)
    def closeEvent(self, event):
        self.settings.setValue('theme', self.current_theme_name)
        if hasattr(self, 'kernel_manager'): self.kernel_manager.shutdown_kernel()
        if hasattr(self, 'terminal_process'): self.terminal_process.kill()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv);
    window = MainWindow();

    sys.exit(app.exec_())
