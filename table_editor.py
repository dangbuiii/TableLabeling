from PyQt5.QtWidgets import QApplication, QWidget, QMenu
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor, QCursor
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
import json


class TableEditor(QWidget):
    cellsChanged = pyqtSignal(list)
    cellSelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle("Table Editor")

        # Background
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.lightGray)
        self.setPalette(p)

        # Image
        self.background_image_path = None
        self.background_pixmap = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Table state
        self.rect = QRectF(0, 0, 800, 600)
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []
        self.merged_cells = set()
        self.header_range = (0, 0)
        self.show_table = True
        self.cell_contents = {}

        # Mouse interaction
        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None
        self.selected_cells = []
        self.dragging_selection = False

    # ----------------------- Utility functions -----------------------
    def map_to_image_coord(self, pt):
        if self.scale_factor == 0:
            return pt.x() - self.offset_x, pt.y() - self.offset_y
        x = (pt.x() - self.offset_x) / self.scale_factor
        y = (pt.y() - self.offset_y) / self.scale_factor
        return x, y

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

    def get_all_cells(self):
        cells = []
        if self.rows == 0 or self.cols == 0:
            return cells

        x_positions = self.get_col_x_positions()
        y_positions = self.get_row_y_positions()

        merged_map = {(r, c): (rs, cs) for (r, c, rs, cs) in self.merged_cells}

        for r in range(self.rows):
            for c in range(self.cols):
                # Merge cell
                if (r, c) in merged_map:
                    rs, cs = merged_map[(r, c)]
                    x0, y0 = x_positions[c], y_positions[r]
                    x1, y1 = x_positions[c + cs], y_positions[r + rs]
                    start_row, end_row = r, r + rs - 1
                    start_col, end_col = c, c + cs - 1
                # Skip merge cell's member
                elif any(rr <= r < rr + rs and cc <= c < cc + cs
                         for (rr, cc, rs, cs) in self.merged_cells):
                    continue

                # Single cell
                else:
                    x0, y0 = x_positions[c], y_positions[r]
                    x1, y1 = x_positions[c + 1], y_positions[r + 1]
                    start_row = end_row = r
                    start_col = end_col = c

                content = self.cell_contents.get((r, c), "")

                cells.append({
                    "bbox": [int(x0), int(y0), int(x1), int(y1)],
                    "start_row": start_row,
                    "end_row": end_row,
                    "start_col": start_col,
                    "end_col": end_col,
                    "content": content
                })

        return cells

    def find_cell_by_point(self, point):
        px, py = point.x(), point.y()

        for cell in self.get_all_cells():
            x0, y0, x1, y1 = cell["bbox"]
            if x0 <= px <= x1 and y0 <= py <= y1:
                return cell

        return None

    def find_cells_in_rect(self, rect: QRectF):
        selected_cells = []
        rect = rect.normalized()

        for cell in self.get_all_cells():
            x0, y0, x1, y1 = cell["bbox"]
            cell_rect = QRectF(x0, y0, x1 - x0, y1 - y0)

            if rect.intersects(cell_rect):
                selected_cells.append(cell)

        return selected_cells

    def get_selected_bound(self):
        min_row = min(c["start_row"] for c in self.selected_cells)
        max_row = max(c["end_row"] for c in self.selected_cells)
        min_col = min(c["start_col"] for c in self.selected_cells)
        max_col = max(c["end_col"] for c in self.selected_cells)

        return min_row, max_row, min_col, max_col

    def update_cells(self):
        all_cells = self.get_all_cells()
        self.cellsChanged.emit(all_cells)

    # ----------------------- Image & Table setup -----------------------
    def set_image(self, image_path):
        self.background_image_path = image_path
        self.background_pixmap = QPixmap(image_path)
        self.rect = QRectF(0, 0, self.background_pixmap.width(), self.background_pixmap.height())

        if self.parent() and hasattr(self.parent(), "viewport"):
            viewport_size = self.parent().viewport().size()
        else:
            viewport_size = self.size()

        if not viewport_size.isEmpty():
            scale_w = viewport_size.width() / self.background_pixmap.width()
            scale_h = viewport_size.height() / self.background_pixmap.height()
            self.scale_factor = min(scale_w, scale_h)
            self.offset_x = (viewport_size.width() - self.background_pixmap.width() * self.scale_factor) / 2
            self.offset_y = (viewport_size.height() - self.background_pixmap.height() * self.scale_factor) / 2
        else:
            self.scale_factor = 1.0
            self.offset_x = self.offset_y = 0

        self.update()

    def create_table(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.col_widths = [self.rect.width() / cols] * cols
        self.row_heights = [self.rect.height() / rows] * rows
        self.merged_cells.clear()
        self.selected_cells = []
        self.header_range = (0, 0)
        self.update()
        self.update_cells()

    def clear_table(self):
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []
        self.merged_cells = set()
        self.selected_cells = []
        self.header_range = (0, 0)
        self.update()
        self.update_cells()

    # ----------------------- Table operations -----------------------
    def select_cell(self, index):
        cell = self.get_all_cells()[index]
        self.selected_cells = [cell]
        self.update()

    def merge_selected_cells(self):
        if not self.selected_cells:
            return

        min_row, max_row, min_col, max_col = self.get_selected_bound()

        self.merge_cell_contents(min_row, min_col, max_row - min_row + 1, max_col - min_col + 1)

        new_merge = (min_row, min_col, max_row - min_row + 1, max_col - min_col + 1)

        for (r0, c0, rs, cs) in list(self.merged_cells):
            r1, r2 = r0, r0 + rs - 1
            c1, c2 = c0, c0 + cs - 1
            if not (max_row < r1 or min_row > r2 or max_col < c1 or min_col > c2):
                self.merged_cells.remove((r0, c0, rs, cs))

        self.merged_cells.add(new_merge)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def unmerge_selected_cells(self):
        if not self.selected_cells:
            return

        min_row, max_row, min_col, max_col = self.get_selected_bound()

        target = None
        for (r0, c0, rs, cs) in list(self.merged_cells):
            if (
                    r0 == min_row
                    and c0 == min_col
                    and (r0 + rs - 1) == max_row
                    and (c0 + cs - 1) == max_col
            ):
                target = (r0, c0, rs, cs)
                break

        if target:
            self.unmerge_cell_contents(min_row, min_col, max_row - min_row + 1, max_col - min_col + 1)
            self.merged_cells.remove(target)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_rows(self):
        if not self.selected_cells:
            return

        min_row, max_row, _, _ = self.get_selected_bound()

        deleted_rows = list(range(min_row + 1, max_row + 1))

        for row_index in deleted_rows:
            self.delete_row_content(row_index)

        for row_index in deleted_rows:
            self.row_heights[min_row] += self.row_heights[row_index]

        del self.row_heights[min_row + 1:max_row + 1]
        self.rows = len(self.row_heights)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_cols(self):
        if not self.selected_cells:
            return

        _, _, min_col, max_col = self.get_selected_bound()

        deleted_cols = list(range(min_col + 1, max_col + 1))

        for col_index in deleted_cols:
            self.delete_col_content(col_index)

        for col_index in deleted_cols:
            self.col_widths[min_col] += self.col_widths[col_index]

        del self.col_widths[min_col + 1:max_col + 1]
        self.cols = len(self.col_widths)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_row(self, n=2):
        if not self.selected_cells or n < 2:
            return

        selected_row = min(c["start_row"] for c in self.selected_cells)

        for _ in range(n - 1):
            self.insert_row_content(selected_row + 1)

        total_height = self.row_heights[selected_row]
        new_height = total_height / n
        self.row_heights[selected_row] = new_height
        for i in range(1, n):
            self.row_heights.insert(selected_row + i, new_height)

        self.rows += n - 1
        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_col(self, n=2):
        if not self.selected_cells or n < 2:
            return

        selected_col = min(c["start_col"] for c in self.selected_cells)

        for _ in range(n - 1):
            self.insert_col_content(selected_col + 1)

        total_width = self.col_widths[selected_col]
        new_width = total_width / n
        self.col_widths[selected_col] = new_width
        for i in range(1, n):
            self.col_widths.insert(selected_col + i, new_width)

        self.cols += n - 1
        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def mark_header(self):
        if not self.selected_cells:
            return

        row_start = min(cell["start_row"] for cell in self.selected_cells)
        row_end = max(cell["end_row"] for cell in self.selected_cells)

        self.header_range = (row_start, row_end)
        self.update()

    # Table content
    def merge_cell_contents(self, top_row, left_col, row_span, col_span):
        merged_texts = []

        for r in range(top_row, top_row + row_span):
            for c in range(left_col, left_col + col_span):
                text = self.cell_contents.pop((r, c), "")
                if text.strip():
                    merged_texts.append(text)

        final_text = " ".join(merged_texts).strip()
        if final_text:
            self.cell_contents[(top_row, left_col)] = final_text

    def unmerge_cell_contents(self, top_row, left_col, row_span, col_span):
        main_text = self.cell_contents.get((top_row, left_col), "")
        for r in range(top_row, top_row + row_span):
            for c in range(left_col, left_col + col_span):
                self.cell_contents[(r, c)] = ""
        self.cell_contents[(top_row, left_col)] = main_text

    def insert_row_content(self, index):
        new_contents = {}
        for (r, c), text in self.cell_contents.items():
            if r >= index:
                new_contents[(r + 1, c)] = text
            else:
                new_contents[(r, c)] = text
        self.cell_contents = new_contents

    def insert_col_content(self, index):
        new_contents = {}
        for (r, c), text in self.cell_contents.items():
            if c >= index:
                new_contents[(r, c + 1)] = text
            else:
                new_contents[(r, c)] = text
        self.cell_contents = new_contents

    def delete_row_content(self, index):
        if not self.cell_contents:
            return

        target_offset = -1 if index > 0 else 1
        new_contents = {}
        for (r, c), text in self.cell_contents.items():
            if r == index:
                target_row = r + target_offset
                if target_row >= 0:
                    old_text = self.cell_contents.get((target_row, c), "")
                    merged = "\n".join([old_text, text]).strip()
                    if merged:
                        new_contents[(target_row, c)] = merged
                continue

            elif r > index:
                new_contents[(r - 1, c)] = text
            else:
                new_contents[(r, c)] = text

        self.cell_contents = new_contents

    def delete_col_content(self, index):
        if not self.cell_contents:
            return

        target_offset = -1 if index > 0 else 1

        new_contents = {}
        for (r, c), text in self.cell_contents.items():
            if c == index:
                target_col = c + target_offset
                if target_col >= 0:
                    old_text = self.cell_contents.get((r, target_col), "")
                    merged = "\n".join([old_text, text]).strip()
                    if merged:
                        new_contents[(r, target_col)] = merged
                continue

            elif c > index:
                new_contents[(r, c - 1)] = text
            else:
                new_contents[(r, c)] = text

        self.cell_contents = new_contents

    # ----------------------- Import / Export -----------------------
    def import_cells(self, filename="table_structure.json"):
        self.clear_table()

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cells = data.get("cells", [])
        self.header_range = tuple(data.get("header", [0, 0]))

        max_row = max(cell["position"][1] for cell in cells) + 1
        max_col = max(cell["position"][3] for cell in cells) + 1
        self.rows, self.cols = max_row, max_col

        col_positions = [float('inf')] * (self.cols + 1)
        row_positions = [float('inf')] * (self.rows + 1)
        max_w = max_h = 0

        for cell in cells:
            x0, y0, x1, y1 = cell["bbox"]
            r0, r1, c0, c1 = cell["position"]
            col_positions[c0] = min(col_positions[c0], x0)
            col_positions[c1 + 1] = min(col_positions[c1 + 1], x1)
            row_positions[r0] = min(row_positions[r0], y0)
            row_positions[r1 + 1] = min(row_positions[r1 + 1], y1)
            max_w, max_h = max(max_w, x1), max(max_h, y1)

            content = ""
            if "token" in cell and cell["token"]:
                content = cell["token"][0]
            self.cell_contents[(r0, c0)] = content

        img_w, img_h = self.background_pixmap.width(), self.background_pixmap.height()
        scale_x = img_w / max_w if max_w > img_w else 1.0
        scale_y = img_h / max_h if max_h > img_h else 1.0

        self.col_widths = [(col_positions[i + 1] - col_positions[i]) * scale_x for i in range(self.cols)]
        self.row_heights = [(row_positions[j + 1] - row_positions[j]) * scale_y for j in range(self.rows)]

        for cell in cells:
            r0, r1, c0, c1 = cell["position"]
            if r1 > r0 or c1 > c0:
                self.merged_cells.add((r0, c0, r1 - r0 + 1, c1 - c0 + 1))

        self.update()
        self.update_cells()

    def export_cells(self, filename="table_structure.json"):
        if self.rows == 0 or self.cols == 0:
            print("Chưa có bảng để xuất.")
            return

        all_cells = self.get_all_cells()

        data = {
            "cells": [],
            "header": list(self.header_range)
        }

        for cell in all_cells:
            data["cells"].append({
                "token": [cell.get("content", "")],
                "bbox": cell["bbox"],
                "position": [
                    cell["start_row"],
                    cell["end_row"],
                    cell["start_col"],
                    cell["end_col"]
                ]
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Successfully export label file: {filename}")

    # ----------------------- Event handlers -----------------------
    def mousePressEvent(self, event):
        if not self.show_table or self.rows == 0 or self.cols == 0:
            return super().mousePressEvent(event)

        x_img, y_img = self.map_to_image_coord(event.pos())
        self.drag_start_pos = (x_img, y_img)
        self.dragging_col = None
        self.dragging_row = None
        self.dragging_selection = False

        col_lines = self.get_col_x_positions()
        row_lines = self.get_row_y_positions()

        # --- Check vertical line ---
        for i in range(1, len(col_lines) - 1):
            if abs(x_img - col_lines[i]) < 10 and self.rect.top() < y_img < self.rect.bottom():
                self.dragging_col = i - 1
                return

        # --- Check horizontal line ---
        for j in range(1, len(row_lines) - 1):
            if abs(y_img - row_lines[j]) < 10 and self.rect.left() < x_img < self.rect.right():
                self.dragging_row = j - 1
                return

        # --- Start selecting ---
        if event.button() == Qt.LeftButton:
            point = QPointF(x_img, y_img)
            cell = self.find_cell_by_point(point)
            if cell:
                self.selected_cells = [cell]
                index = self.get_all_cells().index(cell)
                self.cellSelected.emit(index)
            else:
                self.selected_cells = []
            self.dragging_selection = True
            self.update()

    def mouseMoveEvent(self, event):
        if not self.show_table or self.rows == 0 or self.cols == 0:
            return super().mouseMoveEvent(event)

        x_img, y_img = self.map_to_image_coord(event.pos())
        hovering = False

        # --- Hover horizontal/vertical line ---
        for x_line in self.get_col_x_positions()[1:-1]:
            if abs(x_img - x_line) < 5:
                QApplication.setOverrideCursor(Qt.SplitHCursor)
                hovering = True
                break
        if not hovering:
            for y_line in self.get_row_y_positions()[1:-1]:
                if abs(y_img - y_line) < 5:
                    QApplication.setOverrideCursor(Qt.SplitVCursor)
                    hovering = True
                    break
        if not hovering:
            QApplication.restoreOverrideCursor()

        # --- drag vertical line ---
        if self.dragging_col is not None and self.drag_start_pos is not None:
            i = self.dragging_col
            dx = x_img - self.drag_start_pos[0]

            w_left = self.col_widths[i]
            w_right = self.col_widths[i + 1]

            dx = max(dx, - (w_left - 15))
            dx = min(dx, w_right - 15)

            self.col_widths[i] += dx
            self.col_widths[i + 1] -= dx
            self.drag_start_pos = (x_img, y_img)
            self.update()
            self.update_cells()
            return

        # --- drag horizontal line ---
        if self.dragging_row is not None and self.drag_start_pos is not None:
            j = self.dragging_row
            dy = y_img - self.drag_start_pos[1]

            h_top = self.row_heights[j]
            h_bottom = self.row_heights[j + 1]

            dy = max(dy, - (h_top - 15))
            dy = min(dy, h_bottom - 15)

            self.row_heights[j] += dy
            self.row_heights[j + 1] -= dy
            self.drag_start_pos = (x_img, y_img)
            self.update()
            self.update_cells()
            return

        # --- Select multi cell ---
        if self.dragging_selection and self.drag_start_pos is not None:
            start = QPointF(*self.drag_start_pos)
            end = QPointF(x_img, y_img)
            rect = QRectF(start, end).normalized()
            cells = self.find_cells_in_rect(rect)
            self.selected_cells = cells
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.show_table:
            return super().mouseReleaseEvent(event)

        x_img, y_img = self.map_to_image_coord(event.pos())

        self.dragging_col = None
        self.dragging_row = None

        # --- Stop selecting ---
        if self.dragging_selection:
            self.dragging_selection = False
            start_x, start_y = self.drag_start_pos
            if abs(x_img - start_x) < 3 and abs(y_img - start_y) < 3:
                point = QPointF(x_img, y_img)
                cell = self.find_cell_by_point(point)
                self.selected_cells = [cell] if cell else []

        self.drag_start_pos = None
        self.update()

    def contextMenuEvent(self, event):
        if not self.selected_cells:
            return

        menu = QMenu()
        actions = {}

        min_row, max_row, min_col, max_col = self.get_selected_bound()
        num_rows = max_row - min_row + 1
        num_cols = max_col - min_col + 1

        selected_is_merged = False
        for (r0, c0, rs, cs) in self.merged_cells:
            if (
                    min_row == r0
                    and min_col == c0
                    and max_row == r0 + rs - 1
                    and max_col == c0 + cs - 1
            ):
                selected_is_merged = True
                break

        selected_is_col = (min_row == 0 and max_row == len(self.row_heights) - 1)
        selected_is_row = (min_col == 0 and max_col == len(self.col_widths) - 1)

        if selected_is_merged:
            actions["Unmerge cells"] = menu.addAction("Unmerge cells")
        elif num_cols > 1 or num_rows > 1:
            actions["Merge cells"] = menu.addAction("Merge cells")

        # ---- Submenu Split row ----
        if selected_is_row:
            if num_rows == 1:
                split_row_menu = menu.addMenu("Split row into")
                for n in range(2, 11):
                    act = split_row_menu.addAction(f" {n} rows")
                    act.triggered.connect(lambda checked, x=n: self.split_row(x))
            else:
                actions["Merge rows"] = menu.addAction("Merge rows")

        # ---- Submenu Split column ----
        if selected_is_col:
            if num_cols == 1:
                split_col_menu = menu.addMenu("Split column into")
                for n in range(2, 11):
                    act = split_col_menu.addAction(f" {n} columns")
                    act.triggered.connect(lambda checked, x=n: self.split_col(x))
            else:
                actions["Merge cols"] = menu.addAction("Merge cols")

        if min_row == 0:
            actions["Mark header"] = menu.addAction("Mark rows as header")

        global_pos = QCursor.pos()
        menu.exec_(global_pos)

    def leaveEvent(self, event):
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.show_table = not self.show_table
            self.update()
        if event.key() == Qt.Key_Tab:
            if self.selected_cells:
                index = self.get_all_cells().index(self.selected_cells[0])
                self.select_cell((index + 1) % len(self.get_all_cells()))

    # ----------------------- Rendering -----------------------
    def paintEvent(self, e):
        if not self.background_pixmap:
            return

        p = QPainter(self)
        p.translate(self.offset_x, self.offset_y)
        p.scale(self.scale_factor, self.scale_factor)
        p.drawPixmap(0, 0, self.background_pixmap)

        if not self.show_table or self.rows == 0 or self.cols == 0:
            return

        x = self.get_col_x_positions()
        y = self.get_row_y_positions()

        drawn = set()
        header_cells = []

        # --- Merge cells ---
        p.setPen(QPen(Qt.green, 2))
        for r, c, rs, cs in self.merged_cells:
            x1, y1 = x[c], y[r]
            x2, y2 = x[c + cs], y[r + rs]

            if self.header_range[0] <= r <= self.header_range[1]:
                header_cells.append((x1, y1, x2, y2))

            # Vẽ 4 cạnh đầy đủ
            p.drawLine(int(x1), int(y1), int(x2), int(y1))  # top
            p.drawLine(int(x2), int(y1), int(x2), int(y2))  # right
            p.drawLine(int(x2), int(y2), int(x1), int(y2))  # bottom
            p.drawLine(int(x1), int(y2), int(x1), int(y1))  # left

            for i in range(r, r + rs):
                for j in range(c, c + cs):
                    drawn.add((i, j))

        # --- Single cells ---
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in drawn:
                    continue

                x1, y1 = x[c], y[r]
                x2, y2 = x[c + 1], y[r + 1]

                if self.header_range[0] <= r <= self.header_range[1]:
                    header_cells.append((x1, y1, x2, y2))

                p.drawLine(int(x1), int(y1), int(x2), int(y1))
                p.drawLine(int(x2), int(y1), int(x2), int(y2))
                p.drawLine(int(x2), int(y2), int(x1), int(y2))
                p.drawLine(int(x1), int(y2), int(x1), int(y1))

        # --- Header ---
        p.setPen(QPen(Qt.blue, 2))
        for x1, y1, x2, y2 in header_cells:
            p.drawLine(int(x1), int(y1), int(x2), int(y1))
            p.drawLine(int(x2), int(y1), int(x2), int(y2))
            p.drawLine(int(x2), int(y2), int(x1), int(y2))
            p.drawLine(int(x1), int(y2), int(x1), int(y1))

        # --- Selection ---
        if hasattr(self, "selected_cells") and self.selected_cells:
            min_row, max_row, min_col, max_col = self.get_selected_bound()

            x_positions = self.get_col_x_positions()
            y_positions = self.get_row_y_positions()

            x0 = x_positions[min_col]
            y0 = y_positions[min_row]
            x1 = x_positions[max_col + 1]
            y1 = y_positions[max_row + 1]

            rect = QRectF(int(x0), int(y0), int(x1 - x0), int(y1 - y0))

            # --- Mask ---
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(100, 100, 100, 60))
            p.drawRect(rect)
            p.restore()

            # --- Border ---
            p.setPen(QPen(Qt.red, 3, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect)
