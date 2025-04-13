import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt
from table_editor import TableEditor  # đảm bảo bạn đã tách TableEditor vào file này


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Table Annotator")
        self.resize(1200, 800)

        # Tạo widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Nút mở thư mục ảnh
        btn_open_folder = QPushButton("📂 Mở thư mục ảnh")
        btn_open_folder.clicked.connect(self.open_image_folder)
        layout.addWidget(btn_open_folder)

        # Tạo splitter chia làm 2 phần
        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter)

        # --- Left: Danh sách file ---
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_selected_image)
        self.splitter.addWidget(self.file_list)

        # --- Right: TableEditor ---
        self.editor = TableEditor()
        self.splitter.addWidget(self.editor)
        self.init_menu()

        # Lưu danh sách đường dẫn ảnh
        self.image_files = []
        self.current_image_name = ""

        self.output_dir = None  # Thư mục lưu các file JSON

    def init_menu(self):
        menu_bar = self.menuBar()

        # Menu chỉnh bảng
        table_menu = menu_bar.addMenu("Bảng")

        create_table_action = table_menu.addAction("Tạo bảng mới")
        create_table_action.triggered.connect(self.create_table_dialog)

        export_action = table_menu.addAction("Xuất cấu trúc bảng (JSON)")
        export_action.triggered.connect(self.export_table_label)

        option_menu = menu_bar.addMenu("Tùy chọn")
        set_output_dir_action = option_menu.addAction("Chọn thư mục xuất file")
        set_output_dir_action.triggered.connect(self.set_output_directory)

    def create_table_dialog(self):
        from PyQt5.QtWidgets import QInputDialog

        rows, ok1 = QInputDialog.getInt(self, "Số hàng", "Nhập số hàng:", 10, 1, 100)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "Số cột", "Nhập số cột:", 10, 1, 100)
        if not ok2:
            return
        self.editor.create_table(rows, cols)

    def set_output_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file JSON")
        if folder:
            self.output_dir = folder
            QMessageBox.information(self, "Thành công", f"Đã chọn thư mục lưu: {folder}")

    def export_table_label(self):
        if not self.current_image_name:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ảnh trước khi xuất cấu trúc bảng.")
            return

        if not self.output_dir:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn thư mục xuất file trước.")
            return

        base_name = os.path.splitext(self.current_image_name)[0]
        file_path = os.path.join(self.output_dir, f"{base_name}.json")

        try:
            self.editor.export_cells(file_path)
            QMessageBox.information(self, "Thành công", f"Đã lưu cấu trúc bảng vào:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi khi xuất tệp: {str(e)}")

    def open_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if not folder:
            return

        self.image_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        self.file_list.clear()
        for path in self.image_files:
            self.file_list.addItem(os.path.basename(path))

    def load_selected_image(self, item):
        filename = item.text()
        full_path = next((f for f in self.image_files if os.path.basename(f) == filename), None)
        if full_path:
            self.current_image_name = os.path.basename(full_path)
            self.editor.set_image(full_path)
            self.editor.create_table(1, 1)  # hoặc cho người dùng chọn rows/cols sau


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
