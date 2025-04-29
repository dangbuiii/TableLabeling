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

        # Tạo splitter chia làm 2 phần
        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter)

        # --- Left: Danh sách file ---
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_selected_image)
        self.splitter.addWidget(self.file_list)
        self.file_list.setMinimumWidth(100)
        self.file_list.setMaximumWidth(200)

        # --- Right: TableEditor ---
        self.editor = TableEditor()
        self.editor.setFocus()
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

        # Menu tùy chọn
        option_menu = menu_bar.addMenu("Thư mục")

        open_image_folder_action = option_menu.addAction("Chọn thư mục ảnh")
        open_image_folder_action.triggered.connect(self.open_image_folder)

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
        #Lưu nhãn file hiện tại trước
        if self.current_image_name and self.output_dir:
            try:
                base_name = os.path.splitext(self.current_image_name)[0]
                file_path = os.path.join(self.output_dir, f"{base_name}.json")
                self.editor.export_cells(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không thể lưu ảnh hiện tại:\n{str(e)}")


        filename = item.text()
        full_path = next((f for f in self.image_files if os.path.basename(f) == filename), None)
        if full_path:
            self.current_image_name = os.path.basename(full_path)
            self.editor.set_image(full_path)
            #self.editor.create_table(1, 1)  # hoặc cho người dùng chọn rows/cols sau
            loaded = self.try_load_table_from_json(self.current_image_name)
            if not loaded:
                self.editor.create_table(1, 1)

    def try_load_table_from_json(self, image_name):
        """
        Nếu đã chọn output_dir, kiểm tra xem có file JSON tương ứng với ảnh không.
        Nếu có, gọi editor.import_cells.
        """
        if not self.output_dir:
            return False  # Không có thư mục để tìm file JSON

        json_name = os.path.splitext(image_name)[0] + ".json"
        json_path = os.path.join(self.output_dir, json_name)

        if os.path.exists(json_path):
            try:
                self.editor.import_cells(json_path)
                return True
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Lỗi khi nạp file JSON:\n{str(e)}")
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.load_prev_image()
        elif event.key() == Qt.Key_Right:
            self.load_next_image()

    def load_prev_image(self):
        current_row = self.file_list.currentRow()
        if current_row > 0:
            self.file_list.setCurrentRow(current_row - 1)
            self.load_selected_image(self.file_list.currentItem())

    def load_next_image(self):
        current_row = self.file_list.currentRow()
        if current_row < self.file_list.count() - 1:
            self.file_list.setCurrentRow(current_row + 1)
            self.load_selected_image(self.file_list.currentItem())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
