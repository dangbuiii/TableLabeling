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

    def set_image(self, image_path):
        self.background_image_path = image_path
        self.background_pixmap = QPixmap(self.background_image_path)
        self.rect = QRectF(0, 0, self.background_pixmap.width(), self.background_pixmap.height())
        self.setMinimumSize(self.background_pixmap.size())
        self.update()

    def create_table(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.col_widths = [self.rect.width() / cols] * cols
        self.row_heights = [self.rect.height() / rows] * rows
        self.merged_cells = set()
        self.selected_cell_start = None
        self.selected_cell_end = None
        self.update()

    def export_cells(self, filename="table_structure.json"):
        if self.rows == 0 or self.cols == 0:
            print("Chưa có bảng để xuất.")
            return

        data = {
            "cells": []
        }

        x_positions = self.get_col_x_positions()
        y_positions = self.get_row_y_positions()

        # Keep track of merged cells
        merged_map = {}  # (row, col) -> (row_span, col_span)
        for (r, c, rs, cs) in self.merged_cells:
            merged_map[(r, c)] = (rs, cs)

        # Check if this cell is the start of a merged region
        for row in range(self.rows):
            for col in range(self.cols):
                # Check if this cell is the start of a merged region
                if (row, col) in merged_map:
                    row_span, col_span = merged_map[(row, col)]
                    x0 = x_positions[col]
                    y0 = y_positions[row]
                    x1 = x_positions[col + col_span]
                    y1 = y_positions[row + row_span]
                    data["cells"].append({
                        "token": [],
                        "bbox": [int(x0), int(y0), int(x1), int(y1)]
                    })
                # Skip cells that are part of a merged region but not top-left
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
                        "bbox": [int(x0), int(y0), int(x1), int(y1)]
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
        # Adjust input coordinates to account for zoom
        x /= self.scale_factor
        y /= self.scale_factor

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
            if 0 < self.col_widths[self.dragging_col] + dx < 1000:
                self.col_widths[self.dragging_col] += dx
                self.col_widths[self.dragging_col + 1] -= dx
                # self.drag_start_pos.setX(x)
                self.drag_start_pos.setX(event.pos().x())
                self.update()

        if self.dragging_row is not None:
            # dy = y - self.drag_start_pos.y()
            dy = (event.pos().y() - self.drag_start_pos.y()) / self.scale_factor
            if 0 < self.row_heights[self.dragging_row] + dy < 1000:
                self.row_heights[self.dragging_row] += dy
                self.row_heights[self.dragging_row + 1] -= dy
                # self.drag_start_pos.setY(y)
                self.drag_start_pos.setY(event.pos().y())
                self.update()

    def contextMenuEvent(self, event):
        if self.selected_cell_start and self.selected_cell_end:
            menu = QMenu(self)
            merge_action = menu.addAction("Merge")
            unmerge_action = menu.addAction("Unmerge")
            action = menu.exec_(event.globalPos())

            if action == merge_action:
                self.merge_selected_cells()
            elif action == unmerge_action:
                self.unmerge_selected_cells()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black, 2)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
