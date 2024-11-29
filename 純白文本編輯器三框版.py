import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QMainWindow, QToolButton, QSizePolicy, QLabel, QFileDialog,
    QMessageBox, QShortcut, QDialog, QLineEdit, QCheckBox, QGridLayout,
    QAction, QInputDialog, QSystemTrayIcon, QMenu
)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QTextCursor, QTextDocument,
    QPalette, QColor, QFontDatabase, QPainter, QPixmap
)
from PyQt5.QtCore import Qt, QSize

def resource_path(relative_path):
    """獲取資源的絕對路徑，適用於開發和 PyInstaller 打包後"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ArrowButton(QToolButton):
    """自定義箭頭按鈕"""
    def __init__(self, arrow_type, parent=None):
        super().__init__(parent)
        self.arrow_type = arrow_type
        self.setArrowType(self.arrow_type)
        self.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: #f0f0f0;
                width: 32px;
                height: 32px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """)

    def sizeHint(self):
        return QSize(32, 32)

class FindReplaceDialog(QDialog):
    """查找和替換對話框，支持全局搜索"""
    def __init__(self, parent, text_edit):
        super().__init__(parent=parent)
        self.parent = parent
        self.text_edit = text_edit
        self.current_tab_index = parent.tabs.currentIndex()
        self.current_text_edit_index = 0 if text_edit == parent.tabs.widget(self.current_tab_index).leftTextEdit else (
            1 if text_edit == parent.tabs.widget(self.current_tab_index).middleTextEdit else 2)
        self.last_cursor_position = 0
        self.initUI()

    def initUI(self):
        self.setWindowTitle('搜尋／取代')
        self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        layout = QGridLayout()

        self.find_label = QLabel('搜尋內容:')
        self.find_input = QLineEdit()
        layout.addWidget(self.find_label, 0, 0)
        layout.addWidget(self.find_input, 0, 1)

        self.replace_label = QLabel('取代為:')
        self.replace_input = QLineEdit()
        layout.addWidget(self.replace_label, 1, 0)
        layout.addWidget(self.replace_input, 1, 1)

        self.case_checkbox = QCheckBox('區分大小寫')
        layout.addWidget(self.case_checkbox, 2, 0, 1, 2)

        self.global_checkbox = QCheckBox('全局搜尋')
        layout.addWidget(self.global_checkbox, 3, 0, 1, 2)

        self.find_next_button = QPushButton('搜尋下一個')
        self.find_next_button.clicked.connect(self.find_next)
        layout.addWidget(self.find_next_button, 4, 0)

        self.replace_button = QPushButton('取代')
        self.replace_button.clicked.connect(self.replace_one)
        layout.addWidget(self.replace_button, 4, 1)

        self.replace_all_button = QPushButton('全部取代')
        self.replace_all_button.clicked.connect(self.replace_all)
        layout.addWidget(self.replace_all_button, 5, 0, 1, 2)

        button_style = """
            QPushButton {
                border: none;
                background-color: #f0f0f0;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        self.find_next_button.setStyleSheet(button_style)
        self.replace_button.setStyleSheet(button_style)
        self.replace_all_button.setStyleSheet(button_style)

        self.setLayout(layout)

    def find_next(self):
        search_text = self.find_input.text()
        if not search_text:
            return

        options = QTextDocument.FindFlags()
        if self.case_checkbox.isChecked():
            options |= QTextDocument.FindCaseSensitively

        if self.global_checkbox.isChecked():
            # 全局搜索
            tab_count = self.parent.tabs.count()
            initial_tab_index = self.current_tab_index
            initial_text_edit_index = self.current_text_edit_index
            while True:
                tab = self.parent.tabs.widget(self.current_tab_index)
                text_edits = [tab.leftTextEdit, tab.middleTextEdit, tab.rightTextEdit]
                text_edit = text_edits[self.current_text_edit_index]
                cursor = QTextCursor(text_edit.document())
                cursor.setPosition(self.last_cursor_position)
                cursor = text_edit.document().find(search_text, cursor, options)
                if not cursor.isNull():
                    # 找到匹配項，更新狀態
                    text_edit.setFocus()
                    text_edit.setTextCursor(cursor)
                    self.parent.tabs.setCurrentIndex(self.current_tab_index)
                    self.text_edit = text_edit
                    self.last_cursor_position = cursor.position()
                    self.current_text_edit_index = (
                        0 if text_edit == tab.leftTextEdit else
                        1 if text_edit == tab.middleTextEdit else 2
                    )
                    return
                else:
                    # 在當前文本框未找到，切換到下一個文本框
                    self.current_text_edit_index = (self.current_text_edit_index + 1) % 3
                    if self.current_text_edit_index == 0:
                        # 切換到下一個分頁
                        self.current_tab_index = (self.current_tab_index + 1) % tab_count
                    if (self.current_tab_index == initial_tab_index and
                        self.current_text_edit_index == initial_text_edit_index):
                        # 已經遍歷所有文本框，未找到
                        QMessageBox.information(self, "搜尋", "在所有分頁中找不到搜尋內容")
                        self.reset_search_state()
                        return
                    self.last_cursor_position = 0  # 重置光標位置
        else:
            # 當前文本框搜索
            cursor = self.text_edit.textCursor()
            position = cursor.position()
            cursor = self.text_edit.document().find(search_text, position, options)
            if cursor.isNull():
                # 從文本開頭重新搜索
                cursor = self.text_edit.document().find(search_text, 0, options)
                if cursor.isNull():
                    QMessageBox.information(self, "搜尋", "找不到搜尋內容")
                    return
            self.text_edit.setFocus()
            self.text_edit.setTextCursor(cursor)
            self.last_cursor_position = cursor.position()

    def replace_one(self):
        if self.global_checkbox.isChecked():
            # 全局替換
            cursor = self.text_edit.textCursor()
            if cursor.hasSelection():
                cursor.insertText(self.replace_input.text())
                self.last_cursor_position = cursor.position()
            self.find_next()
        else:
            cursor = self.text_edit.textCursor()
            if not cursor.hasSelection():
                self.find_next()
            if cursor.hasSelection():
                cursor.insertText(self.replace_input.text())
                self.find_next()

    def replace_all(self):
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not search_text:
            return

        options = QTextDocument.FindFlags()
        if self.case_checkbox.isChecked():
            options |= QTextDocument.FindCaseSensitively

        count = 0
        if self.global_checkbox.isChecked():
            # 全局替換
            for tab_index in range(self.parent.tabs.count()):
                tab = self.parent.tabs.widget(tab_index)
                for text_edit in [tab.leftTextEdit, tab.middleTextEdit, tab.rightTextEdit]:
                    cursor = QTextCursor(text_edit.document())
                    while True:
                        cursor = text_edit.document().find(search_text, cursor, options)
                        if cursor.isNull():
                            break
                        cursor.beginEditBlock()
                        cursor.insertText(replace_text)
                        cursor.endEditBlock()
                        count += 1
            QMessageBox.information(self, "取代", f"已全局取代 {count} 個匹配項目")
            self.reset_search_state()
        else:
            # 當前文本框替換
            text_edit = self.text_edit
            cursor = QTextCursor(text_edit.document())
            while True:
                cursor = text_edit.document().find(search_text, cursor, options)
                if cursor.isNull():
                    break
                cursor.beginEditBlock()
                cursor.insertText(replace_text)
                cursor.endEditBlock()
                count += 1
            QMessageBox.information(self, "取代", f"已取代 {count} 個匹配項目")

    def reset_search_state(self):
        self.current_tab_index = self.parent.tabs.currentIndex()
        self.text_edit = self.parent.tabs.widget(self.current_tab_index).leftTextEdit
        self.current_text_edit_index = 0
        self.last_cursor_position = 0

class PlainTextEditor(QMainWindow):
    """主窗口類，包含所有功能實現"""
    def __init__(self):
        super().__init__()
        # 加載自定義字體
        try:
            font_path = resource_path('NotoSansTC.ttf')
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self.font_family = families[0]
                    else:
                        self.font_family = "Microsoft JhengHei"
                else:
                    self.font_family = "Microsoft JhengHei"
            else:
                print(f"Font file not found at: {font_path}")
                self.font_family = "Microsoft JhengHei"
        except Exception as e:
            print(f"Error loading font: {str(e)}")
            self.font_family = "Microsoft JhengHei"
        self.saved_data = "editor_data.json"
        
        # 創建全局調色盤
        self.custom_palette = QPalette()
        self.custom_palette.setColor(QPalette.Highlight, QColor("#a0ffff"))
        self.custom_palette.setColor(QPalette.HighlightedText, QColor("#000000"))
        QApplication.setPalette(self.custom_palette)

        self.initUI()

        # 系統托盤設置
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path('note.ico')))
        
        # 創建托盤菜單
        self.tray_menu = QMenu()
        show_action = self.tray_menu.addAction("顯示")
        quit_action = self.tray_menu.addAction("關閉")
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        self.load_tabs()

    def initUI(self):
        self.setWindowTitle('純白文本編輯器')
        self.setWindowIcon(QIcon(resource_path('note.ico')))
        self.resize(1400, 750)
        self.center()
        self.setStyleSheet("background-color: white;")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setElideMode(Qt.ElideRight)
        self.tabs.setToolTip('可以拖曳分頁標籤來調整順序')

        self.tabs.tabBar().setStyleSheet("""
            QTabBar::scroller {
                width: 32px;
                background: transparent;
            }
            QTabBar QToolButton {
                border: none;
                background-color: #f0f0f0;
                width: 32px;
                height: 32px;
            }
            QTabBar QToolButton::hover {
                background-color: #e0e0e0;
            }
            QTabBar QToolButton::pressed {
                background-color: #d0d0d0;
            }
        """)

        # 替換默認的滾動按鈕
        scroll_area = self.tabs.tabBar().findChild(QToolButton)
        if scroll_area:
            scroll_buttons = scroll_area.findChildren(QToolButton)
            if scroll_buttons:
                for btn in scroll_buttons:
                    arrow_type = btn.arrowType()
                    new_btn = ArrowButton(arrow_type)
                    btn.parent().layout().replaceWidget(btn, new_btn)
                    btn.deleteLater()

        add_tab_button = QToolButton()
        add_tab_button.setText("+")
        add_tab_button.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: #f0f0f0;
                font-size: 14px;
                padding: 5px;
                width: 32px;
                height: 32px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
        """)
        add_tab_button.clicked.connect(self.add_new_tab)
        add_tab_button.setToolTip('點擊以新增一個新分頁')
        self.tabs.setCornerWidget(add_tab_button, Qt.TopLeftCorner)

        self.always_on_top_button = QToolButton()
        self.always_on_top_button.setText("將視窗懸浮顯示在最上層")
        self.always_on_top_button.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: #f0f0f0;
                font-size: 12px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.always_on_top_button.clicked.connect(self.toggle_always_on_top)
        self.always_on_top_button.setToolTip('點擊以將視窗懸浮顯示在最上層，便於多任務操作')
        self.tabs.setCornerWidget(self.always_on_top_button, Qt.TopRightCorner)

    def toggle_always_on_top(self):
        if self.windowFlags() & Qt.WindowStaysOnTopHint:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.always_on_top_button.setText("將視窗懸浮顯示在最上層")
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.always_on_top_button.setText("取消視窗顯示最上層")
        self.show()

    def add_new_tab(self, left_content="", middle_content="", right_content="", title="New Tab"):
        new_tab = QWidget()
        tab_layout = QVBoxLayout()
        left_layout = QVBoxLayout()
        middle_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        leftTextEdit = QTextEdit()
        middleTextEdit = QTextEdit()
        rightTextEdit = QTextEdit()
        leftTextEdit.setAcceptRichText(False)
        middleTextEdit.setAcceptRichText(False)
        rightTextEdit.setAcceptRichText(False)

        font = QFont()
        font.setFamily(self.font_family)
        font.setPointSize(11)
        leftTextEdit.setFont(font)
        middleTextEdit.setFont(font)
        rightTextEdit.setFont(font)

        leftTextEdit.setText(left_content if isinstance(left_content, str) else "")
        middleTextEdit.setText(middle_content if isinstance(middle_content, str) else "")
        rightTextEdit.setText(right_content if isinstance(right_content, str) else "")

        leftTextEdit.setToolTip('此文字框內容的前幾個字元會用於更新分頁標題')
        middleTextEdit.setToolTip('中間文字框')
        rightTextEdit.setToolTip('右側文字框')

        scrollbar_style = """
        QScrollBar:vertical {
            background: transparent;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #e0e0e0;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical {
            background: none;
            height: 0px;
        }
        QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 12px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:horizontal {
            background: #e0e0e0;
            min-width: 20px;
        }
        QScrollBar::add-line:horizontal {
            background: none;
            width: 0px;
        }
        QScrollBar::sub-line:horizontal {
            background: none;
            width: 0px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        """

        text_edit_style = """
            QTextEdit {
                border: 1px solid #d3d3d3;
                background-color: white;
                padding: 5px;
            }
        """ + scrollbar_style

        leftTextEdit.setStyleSheet(text_edit_style)
        middleTextEdit.setStyleSheet(text_edit_style)
        rightTextEdit.setStyleSheet(text_edit_style)

        left_word_count_label = QLabel("字數: 0")
        middle_word_count_label = QLabel("字數: 0")
        right_word_count_label = QLabel("字數: 0")
        word_count_font = QFont()
        word_count_font.setFamily(self.font_family)
        word_count_font.setPointSize(10)
        left_word_count_label.setFont(word_count_font)
        middle_word_count_label.setFont(word_count_font)
        right_word_count_label.setFont(word_count_font)

        leftTextEdit.textChanged.connect(lambda: self.update_word_count(leftTextEdit, left_word_count_label))
        middleTextEdit.textChanged.connect(lambda: self.update_word_count(middleTextEdit, middle_word_count_label))
        rightTextEdit.textChanged.connect(lambda: self.update_word_count(rightTextEdit, right_word_count_label))

        button_style = """
            QPushButton {
                border: none;
                background-color: #f0f0f0;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """

        left_save_button = QPushButton("將左框文字另存新檔")
        middle_save_button = QPushButton("將中框文字另存新檔")
        right_save_button = QPushButton("將右框文字另存新檔")
        left_save_button.setMinimumWidth(200)
        middle_save_button.setMinimumWidth(200)
        right_save_button.setMinimumWidth(200)
        left_save_button.setMaximumWidth(300)
        middle_save_button.setMaximumWidth(300)
        right_save_button.setMaximumWidth(300)
        
        button_font = QFont()
        button_font.setFamily(self.font_family)
        button_font.setPointSize(10)
        left_save_button.setFont(button_font)
        middle_save_button.setFont(button_font)
        right_save_button.setFont(button_font)
        
        left_save_button.setStyleSheet(button_style)
        middle_save_button.setStyleSheet(button_style)
        right_save_button.setStyleSheet(button_style)
        
        left_save_button.clicked.connect(lambda: self.save_file(leftTextEdit))
        middle_save_button.clicked.connect(lambda: self.save_file(middleTextEdit))
        right_save_button.clicked.connect(lambda: self.save_file(rightTextEdit))
        
        left_save_button.setToolTip('將左側文字框的內容另存為檔案')
        middle_save_button.setToolTip('將中間文字框的內容另存為檔案')
        right_save_button.setToolTip('將右側文字框的內容另存為檔案')

        left_layout.addWidget(leftTextEdit)
        left_layout.addWidget(left_word_count_label)
        left_layout.addWidget(left_save_button, alignment=Qt.AlignCenter)

        middle_layout.addWidget(middleTextEdit)
        middle_layout.addWidget(middle_word_count_label)
        middle_layout.addWidget(middle_save_button, alignment=Qt.AlignCenter)

        right_layout.addWidget(rightTextEdit)
        right_layout.addWidget(right_word_count_label)
        right_layout.addWidget(right_save_button, alignment=Qt.AlignCenter)

        text_layout = QHBoxLayout()
        text_layout.addLayout(left_layout)
        text_layout.addLayout(middle_layout)
        text_layout.addLayout(right_layout)

        clear_button = QPushButton('清除當前分頁中所有文本')
        clear_button.setMinimumWidth(250)
        clear_button.setFont(button_font)
        clear_button.setStyleSheet(button_style)
        clear_button.clicked.connect(lambda: self.clear_text([leftTextEdit, middleTextEdit, rightTextEdit]))
        clear_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        clear_button.setToolTip('點擊以清除當前分頁的三個文字框內容，不影響其他分頁')

        tab_layout.addLayout(text_layout)
        tab_layout.addWidget(clear_button, alignment=Qt.AlignCenter)

        new_tab.setLayout(tab_layout)
        self.tabs.addTab(new_tab, title)

        new_tab.leftTextEdit = leftTextEdit
        new_tab.middleTextEdit = middleTextEdit
        new_tab.rightTextEdit = rightTextEdit

        leftTextEdit.textChanged.connect(lambda: self.update_tab_title(leftTextEdit))

        # 為所有文字框添加搜尋和替換快捷鍵
        for text_edit in [leftTextEdit, middleTextEdit, rightTextEdit]:
            search_shortcut = QShortcut(QKeySequence("Ctrl+F"), text_edit, context=Qt.WidgetShortcut)
            search_shortcut.activated.connect(lambda te=text_edit: self.open_find_dialog(te))
            
            replace_shortcut = QShortcut(QKeySequence("Ctrl+H"), text_edit, context=Qt.WidgetShortcut)
            replace_shortcut.activated.connect(lambda te=text_edit: self.open_find_dialog(te))

    def open_find_dialog(self, text_edit):
        dialog = FindReplaceDialog(self, text_edit)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def update_word_count(self, text_edit, label):
        text = text_edit.toPlainText()
        words = len(text.replace('\n', '').replace(' ', '').replace('\t', ''))
        label.setText(f"字數: {words}")

    def update_tab_title(self, text_edit):
        tab_widget = text_edit.parent()
        index = self.tabs.indexOf(tab_widget)
        text = text_edit.toPlainText()
        first_line = text.split('\n', 1)[0]
        tab_title = first_line.strip()[:10] if first_line.strip() else "New Tab"
        self.tabs.setTabText(index, tab_title)

    def close_tab(self, index):
        if self.tabs.count() <= 1:
            return  # 如果只剩一個分頁，不允許關閉
            
        tab = self.tabs.widget(index)
        left_text = tab.leftTextEdit.toPlainText().strip()
        middle_text = tab.middleTextEdit.toPlainText().strip()
        right_text = tab.rightTextEdit.toPlainText().strip()
        
        if left_text == "" and middle_text == "" and right_text == "":
            # 如果三個文本框都為空，直接關閉
            self.tabs.removeTab(index)
        else:
            reply = QMessageBox.question(
                self, '關閉分頁', '確定要關閉這個分頁嗎？未保存的更改將會遺失。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.tabs.removeTab(index)

    def clear_text(self, text_edits):
        for text_edit in text_edits:
            text_edit.clear()

    def save_file(self, text_edit):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(
            self, "另存新檔", "", "Text Files (*.txt);;All Files (*)", options=options
        )
        if fileName:
            encodings = ['UTF-8', 'UTF-16', 'GBK', 'Shift-JIS', 'ISO-8859-1']
            encoding, ok = QInputDialog.getItem(self, "選擇編碼", "請選擇檔案編碼:", encodings, 0, False)
            if ok and encoding:
                try:
                    with open(fileName, 'w', encoding=encoding) as file:
                        file.write(text_edit.toPlainText())
                except Exception as e:
                    QMessageBox.warning(self, "保存失敗", f"保存文件時發生錯誤：{e}")

    def center(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def load_tabs(self):
        if os.path.exists(self.saved_data):
            with open(self.saved_data, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for tab in data.get('tabs', []):
                    left_content = tab.get('left_content', '')
                    middle_content = tab.get('middle_content', '')
                    right_content = tab.get('right_content', '')
                    title = tab.get('title', 'New Tab')
                    self.add_new_tab(left_content, middle_content, right_content, title)
            if self.tabs.count() == 0:
                self.add_new_tab()
        else:
            self.add_new_tab()

    def save_tabs(self):
        data = {
            'tabs': []
        }
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            left_text_edit = tab.leftTextEdit
            middle_text_edit = tab.middleTextEdit
            right_text_edit = tab.rightTextEdit
            data['tabs'].append({
                'left_content': left_text_edit.toPlainText(),
                'middle_content': middle_text_edit.toPlainText(),
                'right_content': right_text_edit.toPlainText(),
                'title': self.tabs.tabText(index)
            })
        with open(self.saved_data, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.save_tabs()
            event.accept()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def quit_application(self):
        self.tray_icon.hide()
        self.save_tabs()
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    editor = PlainTextEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()