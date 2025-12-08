from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QGroupBox, QAction, QPushButton, QMessageBox, QInputDialog,
    QTextEdit, QTableWidget, QAbstractItemView, QTableWidgetItem, QHeaderView,
    QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QSizePolicy,
    QDialog, QVBoxLayout, QLabel, QProgressBar
)

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from table_editor import TableEditor
from auto_labeling import process_single_image, process_folder
import sys
import os

FILE_MISSING = "missing"
FILE_UNCHECKED = "unchecked"
FILE_CHECKED = "checked"

STATUS_ICONS = {
    FILE_MISSING: "❌",
    FILE_UNCHECKED: "⚠️",
    FILE_CHECKED: "✅"
}

class ProcessDialog(QDialog):
    def __init__(self, parent=None, total=0):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.resize(350, 120)

        layout = QVBoxLayout()
        self.label = QLabel("Processing...")
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(total)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)

class FolderProcessWorker(QThread):
    progress = pyqtSignal(int, str)   # (current_index, filename)
    finished = pyqtSignal()

    def __init__(self, image_folder, label_folder):
        super().__init__()
        self.image_folder = image_folder
        self.label_folder = label_folder

    def run(self):
        files = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]

        os.makedirs(self.label_folder, exist_ok=True)

        total = len(files)
        for i, filename in enumerate(files):
            img_path = os.path.join(self.image_folder, filename)
            self.progress.emit(i + 1, filename)

            # Call your existing function
            process_single_image(img_path, self.label_folder)

        self.finished.emit()

class EditorViewer(QGraphicsView):
    def __init__(self, editor_widget):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.proxy = QGraphicsProxyWidget()
        self.proxy.setWidget(editor_widget)
        self.scene.addItem(self.proxy)

        self.table_editor = editor_widget

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scale_factor = 1.0

        self.setMinimumSize(0, 0)
        self.setAlignment(Qt.AlignCenter)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale_view(1.25)
        else:
            self.scale_view(0.8)

    def scale_view(self, factor):
        self.scale_factor *= factor

        self.table_editor.parent_scale_factor *= factor
        self.scale(factor, factor)

    def fit_editor_to_view(self):
        if self.proxy:
            self.fitInView(self.proxy, Qt.KeepAspectRatio)
            self.scale_factor = 1.0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_editor_to_view()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Labeling Tool")
        self.resize(1400, 800)

        # ---- Menu ----
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        select_img_action = QAction("Select image folder", self)
        select_img_action.triggered.connect(self.select_image_folder)
        file_menu.addAction(select_img_action)

        select_label_action = QAction("Select label folder", self)
        select_label_action.triggered.connect(self.select_label_folder)
        file_menu.addAction(select_label_action)

        export_action = QAction("Export current table XML", self)
        export_action.triggered.connect(self.export_table_label)
        file_menu.addAction(export_action)

        tool_menu = menu_bar.addMenu("Tool")

        auto_create_all_action = QAction("Auto Create all table label", self)
        auto_create_all_action.triggered.connect(self.on_auto_create_all)
        tool_menu.addAction(auto_create_all_action)

        # ---- Main layout----
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # ---- (1) File list ----
        self.file_group = QGroupBox("Image Files")
        self.file_group.setFixedWidth(250)
        file_layout = QVBoxLayout(self.file_group)
        file_layout.setContentsMargins(5, 5, 5, 5)
        file_layout.setSpacing(5)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.horizontalHeader().setVisible(False)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.cellClicked.connect(self.on_file_table_clicked)
        self.file_table.currentCellChanged.connect(self.on_file_selection_changed)

        file_layout.addWidget(self.file_table)

        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # cột Status
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # cột File Name

        self.file_table.setColumnWidth(0, 40)  # Status (icon)
        self.file_table.setColumnWidth(1, 160)  # File Name

        main_layout.addWidget(self.file_group)

        # ---- (2) TableEditor ----
        self.image_group = QGroupBox("No image selected")
        image_layout = QVBoxLayout(self.image_group)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        self.table_editor = TableEditor()
        # TableEditor must implement import_cells_xml / export_cells_xml
        self.table_editor.cellsChanged.connect(self.update_cells_info)
        self.table_editor.cellSelected.connect(self.on_cell_selected)

        self.editor_viewer = EditorViewer(self.table_editor)
        self.table_editor.viewer = self.editor_viewer
        self.editor_viewer.setBackgroundBrush(Qt.lightGray)

        image_layout.addWidget(self.editor_viewer)
        main_layout.addWidget(self.image_group, stretch=1)

        # ---- (3) Right area (a+b+c) ----
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # (a) Control Panel
        button_group = QGroupBox("Control Panel")
        button_group.setFixedWidth(290)
        button_group.setFixedHeight(120)
        button_layout = QGridLayout(button_group)
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.setSpacing(8)

        btn_create_label = QPushButton("Create table label")
        btn_auto_label = QPushButton("Auto Create table label")
        btn_save = QPushButton("Save")
        btn_next = QPushButton("Save and Next")

        for btn in [btn_create_label, btn_auto_label, btn_save, btn_next]:
            btn.setFixedSize(130, 40)

        button_layout.addWidget(btn_create_label, 0, 0)
        button_layout.addWidget(btn_auto_label, 0, 1)
        button_layout.addWidget(btn_next, 1, 1)
        button_layout.addWidget(btn_save, 1, 0)
        right_layout.addWidget(button_group)

        btn_create_label.clicked.connect(self.create_table_label)
        btn_auto_label.clicked.connect(self.auto_create_table_label)
        btn_next.clicked.connect(self.save_and_next)
        btn_save.clicked.connect(self.export_table_label)

        # --- Bảng thông tin ô ---
        self.coord_table = QTableWidget()
        self.coord_table.setColumnCount(4)
        self.coord_table.setHorizontalHeaderLabels(["Id", "BBox", "Rows", "Cols"])
        self.coord_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.coord_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.coord_table.setAlternatingRowColors(False)

        header = self.coord_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.resizeSection(0, 40)
        header.resizeSection(1, 130)
        header.resizeSection(2, 59)
        header.resizeSection(3, 59)

        self.coord_table.verticalHeader().setVisible(False)
        self.coord_table.cellClicked.connect(self.on_table_item_clicked)

        right_layout.addWidget(self.coord_table)

        # (c) Cell Content
        content_group = QGroupBox("Empty panel")
        content_group.setFixedWidth(290)
        content_layout = QVBoxLayout(content_group)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(5)

        content_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_layout.addWidget(content_group)
        main_layout.addWidget(right_panel)

        self.image_folder = ""
        self.label_folder = ""
        self.image_count = 0
        self.current_index = 0
        self.current_image_name = ""
        self.current_cell = None
        self.file_status = {}
        self.is_modified = False

    # === Load / Save / Control ==========
    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.load_image_list()
            self.update_file_status()

    def select_label_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Label Folder (for XML)")
        if folder:
            self.label_folder = folder
            QMessageBox.information(self, "Label Folder", f"Selected: {folder}")
            self.update_file_status()

    def update_file_status(self):
        if not self.image_folder or not self.label_folder:
            return

        for row in range(self.file_table.rowCount()):
            fname_item = self.file_table.item(row, 1)
            if not fname_item:
                continue

            fname = fname_item.text()
            xml_path = os.path.join(self.label_folder, os.path.splitext(fname)[0] + ".xml")

            if not os.path.exists(xml_path):
                status = FILE_MISSING
            else:
                prev_status = self.file_status.get(fname, FILE_UNCHECKED)
                status = prev_status if prev_status == FILE_CHECKED else FILE_UNCHECKED

            self.file_status[fname] = status

            status_item = QTableWidgetItem(STATUS_ICONS[status])
            status_item.setFlags(Qt.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.file_table.setItem(row, 0, status_item)

    def load_image_list(self):
        if not self.image_folder:
            return

        image_files = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ]
        self.image_count = len(image_files)

        self.file_table.setRowCount(len(image_files))
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Status"])
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_table.horizontalHeader().setStretchLastSection(True)

        for row, fname in enumerate(image_files):
            name_item = QTableWidgetItem(fname)
            self.file_table.setItem(row, 1, name_item)

            status = FILE_MISSING
            self.file_status[fname] = status

            status_item = QTableWidgetItem(STATUS_ICONS[status])
            status_item.setFlags(Qt.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.file_table.setItem(row, 0, status_item)

        self.file_group.setTitle(f"Image Files (0/{self.image_count})")

    def on_file_table_clicked(self, row, col):
        if self.is_modified:
            current_file = self.current_image_name or "Current file"
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have unsaved changes in \"{current_file}\".\nDo you want to save before switching to another image?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.export_table_label()

        item_name = self.file_table.item(row, 1).text()
        self.current_image_name = item_name
        self.table_editor.clear_table()
        self.table_editor.set_image(os.path.join(self.image_folder, item_name))
        self.image_group.setTitle(item_name)
        self.current_index = row + 1
        self.file_group.setTitle(f"Image Files ({self.current_index}/{self.image_count})")
        self.try_load_table_from_xml(item_name)
        self.editor_viewer.fit_editor_to_view()
        self.is_modified = False

    def create_table_label(self):
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        rows, ok1 = QInputDialog.getInt(self, "Row count", "Enter row count:", 5, 1, 100)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "Column count", "Enter column count:", 5, 1, 100)
        if not ok2:
            return

        self.table_editor.create_table(rows, cols)

    def auto_create_table_label(self):
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        image_path = os.path.join(self.image_folder, self.current_image_name)

        try:
            process_single_image(image_path, self.label_folder)
            self.table_editor.clear_table()
            self.try_load_table_from_xml(self.current_image_name)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Lỗi khi chạy Auto Label:\n{e}")

        self.update_file_status()

    def on_auto_create_all(self):
        if not self.image_folder:
            QMessageBox.warning(self, "Warning", "Please select an image folder first.")
            return
        if not self.label_folder:
            QMessageBox.warning(self, "Warning", "Please select a label folder first.")
            return

        # Lấy danh sách file để xác định tổng số lượng
        files = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]

        # Tạo dialog hiển thị tiến trình
        self.process_dialog = ProcessDialog(self, total=len(files))
        self.process_dialog.show()

        # Tạo worker chạy thread
        self.worker = FolderProcessWorker(self.image_folder, self.label_folder)

        # Kết nối tín hiệu
        self.worker.progress.connect(self.on_process_progress)
        self.worker.finished.connect(self.on_process_finished)

        # Bắt đầu chạy
        self.worker.start()

    def on_process_progress(self, value, filename):
        self.process_dialog.progress.setValue(value)
        self.process_dialog.label.setText(f"Processing: {filename}")

    def on_process_finished(self):
        self.process_dialog.close()
        # Reload file list status icon
        self.update_file_status()

    def try_load_table_from_xml(self, image_name):
        if not self.label_folder:
            return False
        xml_name = os.path.splitext(image_name)[0] + ".xml"
        xml_path = os.path.join(self.label_folder, xml_name)
        if os.path.exists(xml_path):
            try:
                # TableEditor must provide import_cells_xml(filename)
                self.table_editor.import_cells(xml_path)
                return True
            except Exception as e:
                QMessageBox.warning(self, "Load error", f"Error loading XML:\n{e}")
        return False

    def export_table_label(self):
        if not self.label_folder:
            self.select_label_folder()
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "No image selected.")
            return

        base_name = os.path.splitext(self.current_image_name)[0]
        file_path = os.path.join(self.label_folder, f"{base_name}.xml")
        try:
            # TableEditor must provide export_cells_xml(filename)
            self.table_editor.export_cells(file_path)
            self.is_modified = False

            self.file_status[self.current_image_name] = FILE_CHECKED

            for row in range(self.file_table.rowCount()):
                fname_item = self.file_table.item(row, 1)
                if fname_item and fname_item.text() == self.current_image_name:
                    status_item = QTableWidgetItem(STATUS_ICONS[FILE_CHECKED])
                    status_item.setFlags(Qt.ItemIsEnabled)
                    status_item.setTextAlignment(Qt.AlignCenter)
                    self.file_table.setItem(row, 0, status_item)
                    break

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export XML:\n{e}")

    def save_and_next(self):
        self.export_table_label()

        next_row = None
        for row in range(self.file_table.rowCount()):
            fname_item = self.file_table.item(row, 1)
            if fname_item and fname_item.text() == self.current_image_name:
                next_row = row + 1
                break

        if next_row is None or next_row >= self.file_table.rowCount():
            QMessageBox.information(self, "Done", "No more images.")
            return

        self.file_table.selectRow(next_row)
        self.on_file_table_clicked(next_row, 0)

    def update_cells_info(self):
        self.is_modified = True
        cells = self.table_editor.get_all_cells()
        self.coord_table.setRowCount(len(cells))

        for i, cell in enumerate(cells):
            b = cell["bbox"]
            self.coord_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.coord_table.setItem(i, 1, QTableWidgetItem(f"[{b[0]}, {b[1]}, {b[2]}, {b[3]}]"))
            self.coord_table.setItem(i, 2, QTableWidgetItem(f"{cell['start_row']}–>{cell['end_row']}"))
            self.coord_table.setItem(i, 3, QTableWidgetItem(f"{cell['start_col']}–>{cell['end_col']}"))

        self.coord_table.resizeRowsToContents()

    def on_cell_selected(self, index):
        if 0 <= index < self.coord_table.rowCount():
            self.coord_table.selectRow(index)

        self.current_cell = self.table_editor.get_all_cells()[index]

    def on_table_item_clicked(self, row, _):
        self.table_editor.select_cell(row)

    def on_file_selection_changed(self, current_row):
        if current_row < 0:
            return
        self.on_file_table_clicked(current_row, 0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
