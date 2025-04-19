import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QInputDialog,
    QWidget, QAction, QMenu
)
from PyQt5.QtGui import QPainter, QPen, QPixmap
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QScrollArea


class TableEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setWindowTitle("Resizable Table with Merge Function")

        self.rect = QRectF(0, 0, 800, 600)  # sẽ được cập nhật theo ảnh
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []

        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None

        self.selected_cell_start = None
        self.selected_cell_end = None
        self.merged_cells = set()

        self.background_image_path = None
        self.background_pixmap = None

        self.scale_factor = 1.0
        self.header_range = (0, 0)

    def set_image(self, image_path):
        self.background_image_path = image_path
        self.background_pixmap = QPixmap(self.background_image_path)
        self.rect = QRectF(0, 0, self.background_pixmap.width(), self.background_pixmap.height())
        self.setMinimumSize(self.background_pixmap.size())
        self.update()

    def create_table_dialog(self):
        rows, ok1 = QInputDialog.getInt(self, "Số hàng", "Nhập số hàng:", 3, 1, 100)
        cols, ok2 = QInputDialog.getInt(self, "Số cột", "Nhập số cột:", 3, 1, 100)
        if ok1 and ok2:
            self.create_table(rows, cols)

    def create_table(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.col_widths = [self.rect.width() / cols] * cols
        self.row_heights = [self.rect.height() / rows] * rows
        self.merged_cells = set()
        self.selected_cell_start = None
        self.selected_cell_end = None
        self.update()

    def import_cells(self, filename="table_structure.json"):
        with open(filename, "r") as f:
            data = json.load(f)

        cells = data.get("cells", [])
        header_range = tuple(data.get("header", [0, 0]))
        self.header_range = header_range

        # Tìm số hàng, cột lớn nhất
        max_row = max(cell["position"][1] for cell in cells) + 1
        max_col = max(cell["position"][3] for cell in cells) + 1

        self.rows = max_row
        self.cols = max_col

        # Tính toán chiều cao / chiều rộng từ bbox
        col_widths = [0] * self.cols
        row_heights = [0] * self.rows
        col_positions = [float('inf')] * (self.cols + 1)
        row_positions = [float('inf')] * (self.rows + 1)

        for cell in cells:
            x0, y0, x1, y1 = cell["bbox"]
            r0, r1, c0, c1 = cell["position"]

            col_positions[c0] = min(col_positions[c0], x0)
            col_positions[c1 + 1] = min(col_positions[c1 + 1], x1)
            row_positions[r0] = min(row_positions[r0], y0)
            row_positions[r1 + 1] = min(row_positions[r1 + 1], y1)

        # Tính width, height từng cột, hàng
        self.col_widths = []
        self.row_heights = []

        for i in range(self.cols):
            w = col_positions[i + 1] - col_positions[i]
            self.col_widths.append(w)

        for j in range(self.rows):
            h = row_positions[j + 1] - row_positions[j]
            self.row_heights.append(h)

        # Dò các ô gộp
        self.merged_cells = set()
        for cell in cells:
            r0, r1, c0, c1 = cell["position"]
            if r1 > r0 or c1 > c0:
                self.merged_cells.add((r0, c0, r1 - r0 + 1, c1 - c0 + 1))

        self.update()

    def export_cells(self, filename="table_structure.json"):
        if self.rows == 0 or self.cols == 0:
            print("Chưa có bảng để xuất.")
            return

        data = {
            "cells": [],
            "header": list(self.header_range)  # Thêm dòng này để xuất thông tin header
        }

        x_positions = self.get_col_x_positions()
        y_positions = self.get_row_y_positions()

        # Keep track of merged cells
        merged_map = {}  # (row, col) -> (row_span, col_span)
        for (r, c, rs, cs) in self.merged_cells:
            merged_map[(r, c)] = (rs, cs)

        for row in range(self.rows):
            for col in range(self.cols):
                if (row, col) in merged_map:
                    row_span, col_span = merged_map[(row, col)]
                    x0 = x_positions[col]
                    y0 = y_positions[row]
                    x1 = x_positions[col + col_span]
                    y1 = y_positions[row + row_span]
                    data["cells"].append({
                        "token": [],
                        "bbox": [int(x0), int(y0), int(x1), int(y1)],
                        "position": [row, row + row_span - 1, col, col + col_span - 1]
                    })
                elif any(
                        row >= r and row < r + rs and
                        col >= c and col < c + cs and
                        (r, c) != (row, col)
                        for (r, c, rs, cs) in self.merged_cells
                ):
                    continue
                else:
                    x0 = x_positions[col]
                    y0 = y_positions[row]
                    x1 = x_positions[col + 1]
                    y1 = y_positions[row + 1]
                    data["cells"].append({
                        "token": [],
                        "bbox": [int(x0), int(y0), int(x1), int(y1)],
                        "position": [row, row, col, col]
                    })

        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Đã xuất cấu trúc bảng ra file: {filename}")

    def get_col_x_positions(self):
        x_positions = [self.rect.left()]
        for w in self.col_widths:
            x_positions.append(x_positions[-1] + w)
        return x_positions

    def get_row_y_positions(self):
        y_positions = [self.rect.top()]
        for h in self.row_heights:
            y_positions.append(y_positions[-1] + h)
        return y_positions

    def get_cell_at_position(self, x, y):
        col_positions = self.get_col_x_positions()
        row_positions = self.get_row_y_positions()
        for row in range(self.rows):
            for col in range(self.cols):
                left = col_positions[col]
                right = col_positions[col + 1]
                top = row_positions[row]
                bottom = row_positions[row + 1]
                if left <= x <= right and top <= y <= bottom:
                    return (row, col)
        return None

    def merge_selected_cells(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            row_start = min(r1, r2)
            row_end = max(r1, r2)
            col_start = min(c1, c2)
            col_end = max(c1, c2)
            row_span = row_end - row_start + 1
            col_span = col_end - col_start + 1
            self.merged_cells.add((row_start, col_start, row_span, col_span))
            self.update()

    def unmerge_selected_cells(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            row_start = min(r1, r2)
            row_end = max(r1, r2)
            col_start = min(c1, c2)
            col_end = max(c1, c2)

            to_remove = set()
            for (r, c, rs, cs) in self.merged_cells:
                if (
                        row_start <= r + rs - 1 and row_end >= r and
                        col_start <= c + cs - 1 and col_end >= c
                ):
                    to_remove.add((r, c, rs, cs))
            self.merged_cells -= to_remove
            self.update()

    def merge_selected_rows(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            self.selected_cell_start = None
            self.selected_cell_end = None

            row_start = min(r1, r2)
            row_end = max(r1, r2)

            deleted_rows = list(range(row_start + 1, row_end + 1))

        for row_index in deleted_rows:
            self.row_heights[row_start] += self.row_heights[row_index]

        del self.row_heights[row_start + 1:row_end + 1]
        self.rows = len(self.row_heights)

        self.update()

    def merge_selected_cols(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            self.selected_cell_start = None
            self.selected_cell_end = None

            col_start = min(c1, c2)
            col_end = max(c1, c2)

            deleted_cols = list(range(col_start + 1, col_end + 1))

        for col_index in deleted_cols:
            self.col_widths[col_start] += self.col_widths[col_index]

        del self.col_widths[col_start + 1:col_end + 1]
        self.cols = len(self.col_widths)

        self.update()

    def split_row(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            self.selected_cell_start = None
            self.selected_cell_end = None

            selected_row = min(r1, r2)

            half_height = self.row_heights[selected_row] / 2
            self.row_heights[selected_row] = half_height
            self.row_heights.insert(selected_row + 1, half_height)
            self.rows += 1
            self.update()

    def split_col(self):
        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            self.selected_cell_start = None
            self.selected_cell_end = None

            selected_col = min(c1, c2)

            half_width = self.col_widths[selected_col] / 2
            self.col_widths[selected_col] = half_width
            self.col_widths.insert(selected_col + 1, half_width)
            self.cols += 1
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.rows > 0 and self.cols > 0:
            # x, y = event.pos().x(), event.pos().y()
            x = event.pos().x() / self.scale_factor
            y = event.pos().y() / self.scale_factor
            self.drag_start_pos = event.pos()

            col_lines = self.get_col_x_positions()
            row_lines = self.get_row_y_positions()

            for i in range(1, len(col_lines) - 1):
                if abs(x - col_lines[i]) < 5 and self.rect.top() < y < self.rect.bottom():
                    self.dragging_col = i - 1
                    return

            for j in range(1, len(row_lines) - 1):
                if abs(y - row_lines[j]) < 5 and self.rect.left() < x < self.rect.right():
                    self.dragging_row = j - 1
                    return

            self.selected_cell_start = self.get_cell_at_position(x, y)

    def mouseReleaseEvent(self, event):
        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None

        # self.selected_cell_end = self.get_cell_at_position(event.pos().x(), event.pos().y())
        x = event.pos().x() / self.scale_factor
        y = event.pos().y() / self.scale_factor
        self.selected_cell_end = self.get_cell_at_position(x, y)
        self.update()

    def mouseMoveEvent(self, event):
        if self.rows == 0 or self.cols == 0:
            return

        # x, y = event.pos().x(), event.pos().y()
        x = event.pos().x() / self.scale_factor
        y = event.pos().y() / self.scale_factor
        hovering = False

        col_lines = self.get_col_x_positions()
        row_lines = self.get_row_y_positions()

        for i in range(1, len(col_lines) - 1):
            if abs(x - col_lines[i]) < 5 and self.rect.top() < y < self.rect.bottom():
                self.setCursor(Qt.SplitHCursor)
                hovering = True
                break

        if not hovering:
            for j in range(1, len(row_lines) - 1):
                if abs(y - row_lines[j]) < 5 and self.rect.left() < x < self.rect.right():
                    self.setCursor(Qt.SplitVCursor)
                    hovering = True
                    break

        if not hovering and self.dragging_col is None and self.dragging_row is None:
            self.setCursor(Qt.ArrowCursor)

        if self.dragging_col is not None:
            # dx = x - self.drag_start_pos.x()
            dx = (event.pos().x() - self.drag_start_pos.x()) / self.scale_factor
            if 0 < self.col_widths[self.dragging_col] + dx < 10000:
                self.col_widths[self.dragging_col] += dx
                self.col_widths[self.dragging_col + 1] -= dx
                # self.drag_start_pos.setX(x)
                self.drag_start_pos.setX(event.pos().x())
                self.update()

        if self.dragging_row is not None:
            # dy = y - self.drag_start_pos.y()
            dy = (event.pos().y() - self.drag_start_pos.y()) / self.scale_factor
            if 0 < self.row_heights[self.dragging_row] + dy < 10000:
                self.row_heights[self.dragging_row] += dy
                self.row_heights[self.dragging_row + 1] -= dy
                # self.drag_start_pos.setY(y)
                self.drag_start_pos.setY(event.pos().y())
                self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end

            same_cell = (r1 == r2) and (c1 == c2)

            if (r1 == r2) and (c1 == c2): #chỉ chọn 1 ô
                split_row_action = menu.addAction("Tách hàng thành 2 hàng")
                split_col_action = menu.addAction("Tách cột thành 2 cột")
            else:
                merge_action = menu.addAction("Merge cells")
                unmerge_action = menu.addAction("Unmerge cells")
                merge_rows_action = menu.addAction("Gộp các hàng")
                merge_cols_action = menu.addAction("Gộp các cột")


            action = menu.exec_(event.globalPos())

            # Xử lý các hành động
            if action == merge_action:
                self.merge_selected_cells()
            elif action == unmerge_action:
                self.unmerge_selected_cells()
            elif action == split_row_action:
                self.split_row()
            elif action == split_col_action:
                self.split_col()
            elif action == merge_rows_action:
                self.merge_selected_rows()
            elif action == merge_cols_action:
                self.merge_selected_cols()

        else:
            create_table_action = menu.addAction("New table")
            mark_header_action = menu.addAction("Mark Header")

            action = menu.exec_(event.globalPos())

            # Xử lý các hành động
            if action == create_table_action:
                self.create_table_dialog()
            elif action == mark_header_action:
                self.mark_header_dialog()


    def mark_header_dialog(self):
        if self.rows == 0:
            return

        row_start, ok1 = QInputDialog.getInt(self, "Header bắt đầu", "Nhập chỉ số hàng bắt đầu:", 0, 0, self.rows - 1)
        row_end, ok2 = QInputDialog.getInt(self, "Header kết thúc", "Nhập chỉ số hàng kết thúc:", row_start, row_start,
                                           self.rows - 1)

        if ok1 and ok2:
            self.header_range = (row_start, row_end)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.green, 2)
        painter.setPen(pen)

        scale = self.scale_factor

        if self.background_pixmap:
            # scaled = self.background_pixmap.scaled(
            #     int(self.rect.width()), int(self.rect.height()),
            #     Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            # )
            # painter.drawPixmap(self.rect.toRect(), scaled)
            scaled_pixmap = self.background_pixmap.scaled(
                self.background_pixmap.size() * scale,
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)

        if self.rows == 0 or self.cols == 0:
            return

        # x_positions = self.get_col_x_positions()
        # y_positions = self.get_row_y_positions()
        x_positions = [x * scale for x in self.get_col_x_positions()]
        y_positions = [y * scale for y in self.get_row_y_positions()]

        # painter.drawRect(self.rect)
        painter.drawRect(0, 0, int(self.rect.width() * scale), int(self.rect.height() * scale))

        drawn_cells = set()
        for (r, c, rs, cs) in self.merged_cells:
            x = x_positions[c]
            y = y_positions[r]
            w = x_positions[c + cs] - x
            h = y_positions[r + rs] - y
            painter.drawRect(int(x), int(y), int(w), int(h))
            for i in range(r, r + rs):
                for j in range(c, c + cs):
                    drawn_cells.add((i, j))

        for row in range(self.rows):
            for col in range(self.cols):
                if (row, col) in drawn_cells:
                    continue
                x = x_positions[col]
                y = y_positions[row]
                w = x_positions[col + 1] - x
                h = y_positions[row + 1] - y
                painter.drawRect(int(x), int(y), int(w), int(h))

        if self.selected_cell_start and self.selected_cell_end:
            r1, c1 = self.selected_cell_start
            r2, c2 = self.selected_cell_end
            row_start = min(r1, r2)
            row_end = max(r1, r2)
            col_start = min(c1, c2)
            col_end = max(c1, c2)

            x = x_positions[col_start]
            y = y_positions[row_start]
            w = x_positions[col_end + 1] - x
            h = y_positions[row_end + 1] - y

            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            painter.drawRect(int(x), int(y), int(w), int(h))
    def zoom_in(self):
        self.scale_factor *= 1.1
        self.update()

    def zoom_out(self):
        self.scale_factor /= 1.1
        self.update()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Annotator")

        self.editor = TableEditor()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.editor)

        self.setCentralWidget(self.scroll_area)
        self.init_menu()

    def init_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("Tùy chọn")

        open_image_action = QAction("Mở ảnh", self)
        open_image_action.triggered.connect(self.open_image)
        file_menu.addAction(open_image_action)

        new_table_action = QAction("Tạo bảng mới", self)
        new_table_action.triggered.connect(self.create_table)
        file_menu.addAction(new_table_action)

        export_action = QAction("Xuất cấu trúc bảng", self)
        export_action.triggered.connect(self.export_structure)
        file_menu.addAction(export_action)

        import_action = QAction("Nhập cấu trúc bảng", self)
        import_action.triggered.connect(self.import_structure)
        file_menu.addAction(import_action)

        zoom_in_action = QAction("Phóng to", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        file_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Thu nhỏ", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        file_menu.addAction(zoom_out_action)

    def zoom_in(self):
        self.editor.zoom_in()

    def zoom_out(self):
        self.editor.zoom_out()


    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh nền", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            self.editor.set_image(file_path)

    def create_table(self):
        rows, ok1 = QInputDialog.getInt(self, "Số hàng", "Nhập số hàng:", 3, 1, 100)
        cols, ok2 = QInputDialog.getInt(self, "Số cột", "Nhập số cột:", 3, 1, 100)
        if ok1 and ok2:
            self.editor.create_table(rows, cols)

    def export_structure(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu cấu trúc bảng", "table_structure.json",
                                                   "JSON Files (*.json)")
        if file_path:
            self.editor.export_cells(file_path)

    def import_structure(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Chọn file JSON", "", "JSON Files (*.json)")
        if filename:
            self.editor.import_cells(filename)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())