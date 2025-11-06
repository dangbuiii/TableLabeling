import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QListWidget, QLabel, QFileDialog, QGroupBox, QScrollArea,
    QAction, QPushButton, QSizePolicy, QMessageBox, QInputDialog, QTextEdit, QTableWidget, QAbstractItemView,
    QTableWidgetItem, QHeaderView
)

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QSizePolicy
from PyQt5.QtGui import QWheelEvent, QFont

from PyQt5.QtCore import Qt
from table_editor import TableEditor


class EditorViewer(QGraphicsView):
    def __init__(self, editor_widget):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Thêm TableEditor vào scene thông qua Proxy
        self.proxy = QGraphicsProxyWidget()
        self.proxy.setWidget(editor_widget)
        self.scene.addItem(self.proxy)

        # Cuộn & kéo trong vùng TableEditor
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # Zoom quanh tâm
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        # Cho phép mở rộng theo vùng trung tâm
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scale_factor = 1.0

        self.setMinimumSize(0, 0)
        self.setAlignment(Qt.AlignCenter)

    def wheelEvent(self, event):
        # Giống ImageViewer
        if event.angleDelta().y() > 0:
            self.scale_view(1.25)
        else:
            self.scale_view(0.8)

    def scale_view(self, factor):
        self.scale_factor *= factor
        self.scale(factor, factor)

    def fit_editor_to_view(self):
        # Căn TableEditor vừa khung, không thay đổi kích thước editor
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

        export_action = QAction("Export current table JSON", self)
        export_action.triggered.connect(self.export_table_label)
        file_menu.addAction(export_action)

        # ---- Layout chính ----
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # ---- (1) Danh sách file ----
        self.file_group = QGroupBox("Image Files")
        self.file_group.setFixedWidth(250)
        file_layout = QVBoxLayout(self.file_group)
        file_layout.setContentsMargins(5, 5, 5, 5)
        file_layout.setSpacing(5)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list)
        main_layout.addWidget(self.file_group)

        # ---- (2) TableEditor vùng trung tâm ----
        self.image_group = QGroupBox("No image selected")
        image_layout = QVBoxLayout(self.image_group)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        self.table_editor = TableEditor()
        self.table_editor.cellsChanged.connect(self.update_cells_info)
        self.table_editor.cellSelected.connect(self.on_cell_selected)

        self.editor_viewer = EditorViewer(self.table_editor)
        self.table_editor.viewer = self.editor_viewer

        # --- Set nền xám cho EditorViewer ---
        self.editor_viewer.setBackgroundBrush(Qt.lightGray)

        image_layout.addWidget(self.editor_viewer)
        main_layout.addWidget(self.image_group, stretch=1)

        # ---- (3) Vùng phải (a+b+c) ----
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
        btn_ocr = QPushButton("OCR")
        btn_save = QPushButton("Save")

        for btn in [btn_create_label, btn_auto_label, btn_ocr, btn_save]:
            btn.setFixedSize(130, 40)

        button_layout.addWidget(btn_create_label, 0, 0)
        button_layout.addWidget(btn_auto_label, 0, 1)
        button_layout.addWidget(btn_ocr, 1, 0)
        button_layout.addWidget(btn_save, 1, 1)
        right_layout.addWidget(button_group)

        btn_create_label.clicked.connect(self.create_table_label)
        btn_auto_label.clicked.connect(self.auto_create_table_label)
        btn_ocr.clicked.connect(self.run_ocr)
        btn_save.clicked.connect(self.export_table_label)

        # --- Bảng thông tin ô (vùng b) ---
        self.coord_table = QTableWidget()
        self.coord_table.setColumnCount(4)
        self.coord_table.setHorizontalHeaderLabels(["Id", "BBox", "Rows", "Cols"])
        self.coord_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.coord_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.coord_table.setAlternatingRowColors(False)

        header = self.coord_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)  # Cho phép điều chỉnh thủ công
        header.resizeSection(0, 40)
        header.resizeSection(1, 130)
        header.resizeSection(2, 59)
        header.resizeSection(3, 59)

        self.coord_table.verticalHeader().setVisible(False)
        self.coord_table.cellClicked.connect(self.on_table_item_clicked)

        right_layout.addWidget(self.coord_table)

        # (c) Cell Content (co giãn)
        content_group = QGroupBox("Cell Content")
        content_group.setFixedWidth(290)
        content_layout = QVBoxLayout(content_group)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(5)

        self.content_edit = QTextEdit()
        font = QFont()
        font.setPointSize(12)
        self.content_edit.setFont(font)

        self.content_edit.setPlaceholderText("Empty cell")
        self.content_edit.setStyleSheet("border: 1px solid gray;")
        self.content_edit.setEnabled(False)  # chỉ bật khi có ô được chọn
        content_layout.addWidget(self.content_edit)

        # Khi người dùng sửa nội dung
        self.content_edit.textChanged.connect(self.update_cell_content)

        content_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_layout.addWidget(content_group)
        main_layout.addWidget(right_panel)

        # ---- Biến ----
        self.image_folder = ""
        self.label_folder = ""  # dùng làm nơi lưu JSON
        self.image_count = 0
        self.current_index = 0
        self.current_image_name = ""
        self.current_cell = None

    # ==================================================
    # === Load / Save / Điều khiển ảnh & nhãn ==========
    # ==================================================
    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.load_image_list()

    def select_label_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Label Folder (for JSON)")
        if folder:
            self.label_folder = folder
            QMessageBox.information(self, "Label Folder", f"Selected: {folder}")

    def load_image_list(self):
        self.file_list.clear()
        if not self.image_folder:
            return
        image_files = [
            f for f in os.listdir(self.image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ]
        self.image_count = len(image_files)
        for fname in image_files:
            self.file_list.addItem(fname)
        self.file_group.setTitle(f"Image Files (0/{self.image_count})")

    def on_file_selected(self, item):
        image_path = os.path.join(self.image_folder, item.text())
        self.current_image_name = item.text()
        self.table_editor.set_image(image_path)
        self.table_editor.clear_table()
        self.image_group.setTitle(item.text())

        self.current_index = self.file_list.row(item) + 1
        self.file_group.setTitle(f"Image Files ({self.current_index}/{self.image_count})")

        # Load table nếu có file JSON
        self.try_load_table_from_json(self.current_image_name)

        self.editor_viewer.fit_editor_to_view()

    def create_table_label(self):
        """Tạo bảng trống thủ công"""
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        rows, ok1 = QInputDialog.getInt(self, "Số hàng", "Nhập số hàng:", 10, 1, 100)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "Số cột", "Nhập số cột:", 10, 1, 100)
        if not ok2:
            return

        self.table_editor.create_table(rows, cols)

    def auto_create_table_label(self):
        """Tạo bảng tự động (placeholder — bạn có thể tích hợp thuật toán sau)"""
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        # Gọi hàm AI hoặc OCR tự động xác định bảng (tạm thời dùng ví dụ)
        self.table_editor.auto_detect_table()
        QMessageBox.information(self, "Auto Label", "Auto-created table labels from image.")

    def run_ocr(self):
        """Chạy OCR để nhận dạng nội dung từng ô"""
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        try:
            self.table_editor.run_ocr()
            QMessageBox.information(self, "OCR", "OCR completed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "OCR Error", f"OCR failed:\n{e}")

    def try_load_table_from_json(self, image_name):
        """Tự động nạp file JSON từ label_folder nếu có"""
        if not self.label_folder:
            return False
        json_name = os.path.splitext(image_name)[0] + ".json"
        json_path = os.path.join(self.label_folder, json_name)
        if os.path.exists(json_path):
            try:
                self.table_editor.import_cells(json_path)
                return True
            except Exception as e:
                QMessageBox.warning(self, "Load error", f"Error loading JSON:\n{e}")
        return False

    def export_table_label(self):
        """Xuất file JSON vào label_folder"""
        if not self.label_folder:
            QMessageBox.warning(self, "Warning", "Please select label folder first.")
            return
        if not self.current_image_name:
            QMessageBox.warning(self, "Warning", "No image selected.")
            return
        base_name = os.path.splitext(self.current_image_name)[0]
        file_path = os.path.join(self.label_folder, f"{base_name}.json")
        try:
            self.table_editor.export_cells(file_path)
            QMessageBox.information(self, "Success", f"Saved table to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export JSON:\n{e}")

    def update_cells_info(self):
        cells = self.table_editor.get_all_cells()
        self.coord_table.setRowCount(len(cells))

        for i, cell in enumerate(cells):
            b = cell["bbox"]
            self.coord_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.coord_table.setItem(i, 1, QTableWidgetItem(f"[{b[0]}, {b[1]}, {b[2]}, {b[3]}]"))
            self.coord_table.setItem(i, 2, QTableWidgetItem(f"{cell['start_row']}–>{cell['end_row']}"))
            self.coord_table.setItem(i, 3, QTableWidgetItem(f"{cell['start_col']}–>{cell['end_col']}"))

        self.coord_table.resizeRowsToContents()

    def update_cell_content(self):
        if not hasattr(self, "current_cell") or self.current_cell is None:
            return
        new_text = self.content_edit.toPlainText()
        # update table content
        r, c = self.current_cell['start_row'], self.current_cell['start_col']
        self.table_editor.cell_contents[(r, c)] = new_text

    def on_cell_selected(self, index):
        if 0 <= index < self.coord_table.rowCount():
            self.coord_table.selectRow(index)

        self.current_cell = self.table_editor.get_all_cells()[index]
        self.content_edit.setEnabled(True)
        self.content_edit.blockSignals(True)
        self.content_edit.setPlainText(self.current_cell.get("content", ""))
        self.content_edit.blockSignals(False)

    def on_table_item_clicked(self, row, col):
        self.table_editor.select_cell(row)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.load_prev_image()
        elif event.key() == Qt.Key_Right:
            self.load_next_image()

    def load_prev_image(self):
        current_row = self.file_list.currentRow()
        if current_row > 0:
            self.file_list.setCurrentRow(current_row - 1)
            self.on_file_selected(self.file_list.currentItem())

    def load_next_image(self):
        current_row = self.file_list.currentRow()
        if current_row < self.file_list.count() - 1:
            self.file_list.setCurrentRow(current_row + 1)
            self.on_file_selected(self.file_list.currentItem())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
