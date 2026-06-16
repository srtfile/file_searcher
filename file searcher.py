import sys
import os
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QSplitter,
    QMenu,
)

from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QUrl,
)

from PyQt6.QtGui import (
    QFont,
    QDesktopServices,
    QAction,
)


# ==========================================
# SEARCH THREAD
# ==========================================
class SearchThread(QThread):

    result_found = pyqtSignal(str, str)
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished_search = pyqtSignal()

    def __init__(
        self,
        directory,
        pattern,
        search_mode,
        extensions,
        case_sensitive,
    ):
        super().__init__()

        self.directory = directory
        self.pattern = pattern
        self.search_mode = search_mode
        self.extensions = extensions
        self.case_sensitive = case_sensitive
        self.running = True

    def stop(self):
        self.running = False

    # ==========================================
    # SEARCH LOGIC
    # ==========================================
    def run(self):

        all_files = []

        # Collect all files
        for root, dirs, files in os.walk(self.directory):

            if not self.running:
                return

            for file in files:

                ext = Path(file).suffix.lower()

                if ext in self.extensions:

                    full_path = os.path.join(root, file)
                    all_files.append(full_path)

        total_files = len(all_files)

        if total_files == 0:
            self.status_update.emit("No matching files found.")
            self.finished_search.emit()
            return

        found_count = 0

        # Scan files
        for index, filepath in enumerate(all_files):

            if not self.running:
                return

            self.status_update.emit(f"Scanning: {filepath}")

            try:
                with open(
                    filepath,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    lines = f.readlines()

                    for line_number, line in enumerate(lines, start=1):

                        if self.match_pattern(line):

                            found_count += 1

                            preview = line.strip()

                            result_text = (
                                f"\n"
                                f"FILE: {filepath}\n"
                                f"LINE: {line_number}\n"
                                f"MATCH: {preview}\n"
                                f"{'-'*70}"
                            )

                            self.result_found.emit(
                                result_text,
                                filepath
                            )

            except Exception as e:

                self.result_found.emit(
                    f"\nERROR reading:\n{filepath}\n{str(e)}",
                    filepath
                )

            progress = int((index + 1) / total_files * 100)
            self.progress_update.emit(progress)

        self.status_update.emit(
            f"Search completed. Found {found_count} matches."
        )

        self.finished_search.emit()

    # ==========================================
    # MATCHER
    # ==========================================
    def match_pattern(self, line):

        if not self.case_sensitive:
            target_line = line.lower()
            target_pattern = self.pattern.lower()
        else:
            target_line = line
            target_pattern = self.pattern

        # Exact text
        if self.search_mode == "Exact Text":

            return target_pattern in target_line

        # Regex
        elif self.search_mode == "Regex":

            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                return re.search(self.pattern, line, flags)

            except:
                return False

        # URL Mode
        elif self.search_mode == "URL":

            url_regex = r"https?://[^\s\"'>]+"

            urls = re.findall(url_regex, line)

            for url in urls:

                compare_url = (
                    url if self.case_sensitive
                    else url.lower()
                )

                if target_pattern in compare_url:
                    return True

        return False


# ==========================================
# MAIN WINDOW
# ==========================================
class AdvancedFileSearcher(QWidget):

    def __init__(self):

        super().__init__()

        self.search_thread = None

        self.setWindowTitle(
            "🔥 Advanced Local File Searcher"
        )

        self.resize(1300, 800)

        self.init_ui()

    # ==========================================
    # UI
    # ==========================================
    def init_ui(self):

        main_layout = QVBoxLayout()

        # ==========================================
        # TITLE
        # ==========================================
        title = QLabel(
            "🔥 Advanced Local File Searcher"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)

        title.setFont(title_font)

        # ==========================================
        # DIRECTORY
        # ==========================================
        dir_layout = QHBoxLayout()

        self.dir_input = QLineEdit()

        self.dir_input.setPlaceholderText(
            "Select folder..."
        )

        browse_btn = QPushButton("Browse")

        browse_btn.clicked.connect(
            self.browse_directory
        )

        dir_layout.addWidget(QLabel("Directory:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)

        # ==========================================
        # SEARCH
        # ==========================================
        pattern_layout = QHBoxLayout()

        self.pattern_input = QLineEdit()

        self.pattern_input.setPlaceholderText(
            "Enter search text, regex, URL..."
        )

        self.search_mode = QComboBox()

        self.search_mode.addItems([
            "Exact Text",
            "Regex",
            "URL"
        ])

        self.case_checkbox = QCheckBox(
            "Case Sensitive"
        )

        pattern_layout.addWidget(QLabel("Search:"))
        pattern_layout.addWidget(self.pattern_input)
        pattern_layout.addWidget(self.search_mode)
        pattern_layout.addWidget(self.case_checkbox)

        # ==========================================
        # EXTENSIONS
        # ==========================================
        ext_layout = QHBoxLayout()

        self.html_check = QCheckBox(".html")
        self.py_check = QCheckBox(".py")
        self.txt_check = QCheckBox(".txt")
        self.js_check = QCheckBox(".js")
        self.css_check = QCheckBox(".css")
        self.json_check = QCheckBox(".json")

        self.html_check.setChecked(True)
        self.py_check.setChecked(True)
        self.txt_check.setChecked(True)
        self.js_check.setChecked(True)

        ext_layout.addWidget(QLabel("Extensions:"))
        ext_layout.addWidget(self.html_check)
        ext_layout.addWidget(self.py_check)
        ext_layout.addWidget(self.txt_check)
        ext_layout.addWidget(self.js_check)
        ext_layout.addWidget(self.css_check)
        ext_layout.addWidget(self.json_check)

        # ==========================================
        # BUTTONS
        # ==========================================
        button_layout = QHBoxLayout()

        self.search_btn = QPushButton(
            "🔍 Start Search"
        )

        self.stop_btn = QPushButton(
            "🛑 Stop"
        )

        self.clear_btn = QPushButton(
            "🧹 Clear"
        )

        self.stop_btn.setEnabled(False)

        self.search_btn.clicked.connect(
            self.start_search
        )

        self.stop_btn.clicked.connect(
            self.stop_search
        )

        self.clear_btn.clicked.connect(
            self.clear_results
        )

        button_layout.addWidget(self.search_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)

        # ==========================================
        # STATUS
        # ==========================================
        self.progress = QProgressBar()

        self.status_label = QLabel("Ready")

        # ==========================================
        # FILE LIST
        # ==========================================
        self.file_list = QListWidget()

        # Double click open
        self.file_list.itemDoubleClicked.connect(
            self.open_selected_file
        )

        # Right click menu
        self.file_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.file_list.customContextMenuRequested.connect(
            self.show_context_menu
        )

        # ==========================================
        # RESULT BOX
        # ==========================================
        self.result_box = QTextEdit()

        self.result_box.setReadOnly(True)

        # ==========================================
        # SPLITTER
        # ==========================================
        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.addWidget(self.file_list)
        splitter.addWidget(self.result_box)

        splitter.setSizes([350, 950])

        # ==========================================
        # ADD TO LAYOUT
        # ==========================================
        main_layout.addWidget(title)
        main_layout.addLayout(dir_layout)
        main_layout.addLayout(pattern_layout)
        main_layout.addLayout(ext_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        # ==========================================
        # STYLE
        # ==========================================
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: white;
                font-size: 13px;
            }

            QLineEdit,
            QTextEdit,
            QListWidget,
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 5px;
            }

            QPushButton {
                background-color: #0066cc;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #0080ff;
            }

            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #00aa00;
            }
        """)

    # ==========================================
    # BROWSE DIRECTORY
    # ==========================================
    def browse_directory(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Directory"
        )

        if folder:
            self.dir_input.setText(folder)

    # ==========================================
    # START SEARCH
    # ==========================================
    def start_search(self):

        directory = self.dir_input.text().strip()

        pattern = self.pattern_input.text().strip()

        if not directory:

            QMessageBox.warning(
                self,
                "Error",
                "Please select directory."
            )

            return

        if not pattern:

            QMessageBox.warning(
                self,
                "Error",
                "Please enter search pattern."
            )

            return

        extensions = []

        if self.html_check.isChecked():
            extensions.append(".html")

        if self.py_check.isChecked():
            extensions.append(".py")

        if self.txt_check.isChecked():
            extensions.append(".txt")

        if self.js_check.isChecked():
            extensions.append(".js")

        if self.css_check.isChecked():
            extensions.append(".css")

        if self.json_check.isChecked():
            extensions.append(".json")

        if not extensions:

            QMessageBox.warning(
                self,
                "Error",
                "Select at least one extension."
            )

            return

        self.result_box.clear()
        self.file_list.clear()

        self.progress.setValue(0)

        self.search_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.search_thread = SearchThread(
            directory=directory,
            pattern=pattern,
            search_mode=self.search_mode.currentText(),
            extensions=extensions,
            case_sensitive=self.case_checkbox.isChecked(),
        )

        self.search_thread.result_found.connect(
            self.add_result
        )

        self.search_thread.progress_update.connect(
            self.progress.setValue
        )

        self.search_thread.status_update.connect(
            self.status_label.setText
        )

        self.search_thread.finished_search.connect(
            self.search_finished
        )

        self.search_thread.start()

    # ==========================================
    # STOP SEARCH
    # ==========================================
    def stop_search(self):

        if self.search_thread:
            self.search_thread.stop()

        self.status_label.setText(
            "Search stopped."
        )

        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ==========================================
    # ADD RESULT
    # ==========================================
    def add_result(self, text, filepath):

        self.result_box.append(text)

        existing = []

        for i in range(self.file_list.count()):

            existing.append(
                self.file_list.item(i).text()
            )

        if filepath not in existing:

            self.file_list.addItem(
                QListWidgetItem(filepath)
            )

    # ==========================================
    # SEARCH FINISHED
    # ==========================================
    def search_finished(self):

        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ==========================================
    # CLEAR
    # ==========================================
    def clear_results(self):

        self.result_box.clear()
        self.file_list.clear()

        self.progress.setValue(0)

        self.status_label.setText("Ready")

    # ==========================================
    # OPEN FILE
    # ==========================================
    def open_selected_file(self, item):

        filepath = item.text()

        if os.path.exists(filepath):

            QDesktopServices.openUrl(
                QUrl.fromLocalFile(filepath)
            )

        else:

            QMessageBox.warning(
                self,
                "Missing File",
                "File no longer exists."
            )

    # ==========================================
    # RIGHT CLICK MENU
    # ==========================================
    def show_context_menu(self, position):

        item = self.file_list.itemAt(position)

        if item is None:
            return

        filepath = item.text()

        menu = QMenu()

        open_action = QAction("Open File", self)

        folder_action = QAction(
            "Open Containing Folder",
            self
        )

        copy_action = QAction(
            "Copy Full Path",
            self
        )

        menu.addAction(open_action)
        menu.addAction(folder_action)
        menu.addAction(copy_action)

        action = menu.exec(
            self.file_list.mapToGlobal(position)
        )

        # Open file
        if action == open_action:

            QDesktopServices.openUrl(
                QUrl.fromLocalFile(filepath)
            )

        # Open folder
        elif action == folder_action:

            folder = os.path.dirname(filepath)

            QDesktopServices.openUrl(
                QUrl.fromLocalFile(folder)
            )

        # Copy path
        elif action == copy_action:

            QApplication.clipboard().setText(
                filepath
            )

            QMessageBox.information(
                self,
                "Copied",
                "File path copied."
            )


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = AdvancedFileSearcher()

    window.show()

    sys.exit(app.exec())