from PyQt5.QtWidgets import QApplication, QWidget, QMenu
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor, QCursor
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal

from converter import boxes_to_voc_xml, voc_xml_to_boxes
from table import Table


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

        # Table
        self.table = None
        self.edit_enabled = True

        # Mouse interaction
        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None
        self.selected_cells = []
        self.dragging_selection = False
        self.hover_col = None
        self.hover_row = None

    def hit_tolerance(self):
        view = self.parent()
        if view and hasattr(view, "transform"):
            scale = view.transform().m11()
            if scale > 0:
                return max(4, 8 / scale)
        return 5

    def get_selected_bound(self):
        if not self.selected_cells:
            return None

        min_row = min(c["position"][0] for c in self.selected_cells)
        max_row = max(c["position"][0] + c["position"][2] - 1 for c in self.selected_cells)

        min_col = min(c["position"][1] for c in self.selected_cells)
        max_col = max(c["position"][1] + c["position"][3] - 1 for c in self.selected_cells)

        return min_row, max_row, min_col, max_col

    def update_cells(self):
        if self.table is not None:
            all_cells = self.table.get_all_cells()
            self.cellsChanged.emit(all_cells)

    # ----------------------- Image & Table setup -----------------------
    def set_image(self, image_path):
        self.background_image_path = image_path
        self.background_pixmap = QPixmap(image_path)

        if self.background_pixmap.isNull():
            return

        self.setFixedSize(
            self.background_pixmap.width(),
            self.background_pixmap.height()
        )

        self.update()

    def create_table(self, rows, cols):
        if not self.background_pixmap:
            return

        img_w = self.background_pixmap.width()
        img_h = self.background_pixmap.height()

        col_widths = [img_w / cols] * cols
        row_heights = [img_h / rows] * rows

        self.table = Table(
            col_widths=col_widths,
            row_heights=row_heights,
            merged_cells=[]
        )

        self.selected_cells = []
        self.update()
        self.update_cells()

    def clear_table(self):
        self.table = None
        self.update()
        self.update_cells()

    # ----------------------- Table operations -----------------------
    def merge_selected_cells(self):
        if not self.selected_cells:
            return

        self.table.merge_cells(self.selected_cells)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def unmerge_selected_cells(self):
        if not self.selected_cells:
            return

        r, c, _, _ = self.selected_cells[0]["position"]
        self.table.unmerge_cell(r, c)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_rows(self):
        if not self.selected_cells:
            return

        min_row, max_row, _, _ = self.get_selected_bound()

        for r in range(min_row + 1, max_row + 1):
            self.table.row_heights[min_row] += self.table.row_heights[r]

        for r in range(max_row, min_row, -1):
            self.table.delete_row(r)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_cols(self):
        if not self.selected_cells:
            return

        _, _, min_col, max_col = self.get_selected_bound()

        for c in range(min_col + 1, max_col + 1):
            self.table.col_widths[min_col] += self.table.col_widths[c]

        for c in range(max_col, min_col, -1):
            self.table.delete_col(c)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_row(self, n=2):
        if not self.selected_cells or n < 2:
            return

        r, _, _, _ = self.selected_cells[0]["position"]

        total_h = self.table.row_heights[r]
        new_h = total_h / n
        self.table.row_heights[r] = new_h

        for i in range(1, n):
            self.table.insert_row(r + i, new_h)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_col(self, n=2):
        if not self.selected_cells or n < 2:
            return

        _, c, _, _ = self.selected_cells[0]["position"]

        total_w = self.table.col_widths[c]
        new_w = total_w / n
        self.table.col_widths[c] = new_w

        for i in range(1, n):
            self.table.insert_col(c + i, new_w)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def import_cells(self, filename):
        boxes = voc_xml_to_boxes(filename)

        rows = []
        cols = []
        merged_boxes = []

        for obj in boxes:
            name = obj["label"]
            xmin, ymin, xmax, ymax = obj["bbox"]

            if name == "table row":
                rows.append((ymin, ymax))
            elif name == "table column":
                cols.append((xmin, xmax))
            elif name == "table spanning cell":
                merged_boxes.append((xmin, ymin, xmax, ymax))

        rows.sort(key=lambda x: x[0])
        cols.sort(key=lambda x: x[0])

        if not rows or not cols:
            return

        img_w = self.background_pixmap.width()
        img_h = self.background_pixmap.height()

        # normalize borders
        rows[0] = (0, rows[0][1])
        rows[-1] = (rows[-1][0], img_h)
        cols[0] = (0, cols[0][1])
        cols[-1] = (cols[-1][0], img_w)

        # sizes
        row_heights = [
            rows[i + 1][0] - rows[i][0]
            for i in range(len(rows) - 1)
        ]
        row_heights.append(rows[-1][1] - rows[-1][0])

        col_widths = [
            cols[i + 1][0] - cols[i][0]
            for i in range(len(cols) - 1)
        ]
        col_widths.append(cols[-1][1] - cols[-1][0])

        # helper: bbox → span
        def find_span(box):
            x0, y0, x1, y1 = box

            r0 = min(range(len(rows)), key=lambda i: abs(y0 - rows[i][0]))
            r1 = min(range(len(rows)), key=lambda i: abs(y1 - rows[i][1]))
            c0 = min(range(len(cols)), key=lambda i: abs(x0 - cols[i][0]))
            c1 = min(range(len(cols)), key=lambda i: abs(x1 - cols[i][1]))

            return r0, c0, r1 - r0 + 1, c1 - c0 + 1

        merged_cells = set()
        for box in merged_boxes:
            r, c, rs, cs = find_span(box)
            if rs > 1 or cs > 1:
                merged_cells.add((r, c, rs, cs))

        self.table = Table(col_widths, row_heights, merged_cells)
        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def export_cells(self, filename):
        if self.table is None:
            return

        col_pos = [0]
        for w in self.table.col_widths:
            col_pos.append(col_pos[-1] + w)

        row_pos = [0]
        for h in self.table.row_heights:
            row_pos.append(row_pos[-1] + h)

        objects = []

        # table
        objects.append({
            "label": "table",
            "bbox": (0, 0, col_pos[-1], row_pos[-1])
        })

        # rows
        for y0, y1 in zip(row_pos[:-1], row_pos[1:]):
            objects.append({
                "label": "table row",
                "bbox": (0, y0, col_pos[-1], y1)
            })

        # cols
        for x0, x1 in zip(col_pos[:-1], col_pos[1:]):
            objects.append({
                "label": "table column",
                "bbox": (x0, 0, x1, row_pos[-1])
            })

        # merged cells
        for r, c, rs, cs in self.table.merged_cells:
            x0 = col_pos[c]
            x1 = col_pos[c + cs]
            y0 = row_pos[r]
            y1 = row_pos[r + rs]
            objects.append({
                "label": "table spanning cell",
                "bbox": (x0, y0, x1, y1)
            })

        boxes_to_voc_xml(
            objects,
            filename,
            image_size=(
                self.background_pixmap.width(),
                self.background_pixmap.height(),
                3
            )
        )

    # ----------------------- Event handlers -----------------------
    def mousePressEvent(self, event):
        if not self.edit_enabled or self.table is None:
            return super().mousePressEvent(event)

        p = event.pos()
        x_img, y_img = p.x(), p.y()

        self.drag_start_pos = (x_img, y_img)
        self.dragging_col = None
        self.dragging_row = None
        self.dragging_selection = False

        if self.hover_col is not None:
            self.dragging_col = self.hover_col
            self.drag_start_pos = (x_img, y_img)
            return

        if self.hover_row is not None:
            self.dragging_row = self.hover_row
            self.drag_start_pos = (x_img, y_img)
            return

        # --- Start selecting ---
        if event.button() == Qt.LeftButton:
            cell = self.table.get_cell_at((x_img, y_img))
            if cell:
                self.selected_cells = [{"position": cell["position"]}]
                index = self.table.get_all_cells().index(cell)
                self.cellSelected.emit(index)
            else:
                self.selected_cells = []
            self.dragging_selection = True
            self.update()

    def mouseMoveEvent(self, event):
        if not self.edit_enabled or self.table is None:
            return super().mouseMoveEvent(event)

        p = event.pos()
        x_img, y_img = p.x(), p.y()

        tol = self.hit_tolerance()

        self.hover_col = None
        self.hover_row = None

        # vertical
        for i, x_line in enumerate(self.table.get_col_x_positions()[1:-1]):
            if abs(x_img - x_line) < tol:
                self.hover_col = i
                break

        # horizontal
        if self.hover_col is None:
            for j, y_line in enumerate(self.table.get_row_y_positions()[1:-1]):
                if abs(y_img - y_line) < tol:
                    self.hover_row = j
                    break

        # cursor
        if self.hover_col is not None:
            QApplication.setOverrideCursor(Qt.SplitHCursor)
        elif self.hover_row is not None:
            QApplication.setOverrideCursor(Qt.SplitVCursor)
        elif self.dragging_col is None and self.dragging_row is None:
            QApplication.restoreOverrideCursor()

        # --- drag vertical line ---
        if self.dragging_col is not None and self.drag_start_pos is not None:
            QApplication.setOverrideCursor(Qt.SplitHCursor)

            i = self.dragging_col
            dx = x_img - self.drag_start_pos[0]

            w_left = self.table.col_widths[i]
            w_right = self.table.col_widths[i + 1]

            dx = max(dx, -(w_left - 15))
            dx = min(dx, (w_right - 15))

            if abs(dx) > 0:
                self.table.col_widths[i] += dx
                self.table.col_widths[i + 1] -= dx
                self.drag_start_pos = (x_img, y_img)
                self.update()
                self.update_cells()

            return

        # --- drag horizontal line ---
        if self.dragging_row is not None and self.drag_start_pos is not None:
            QApplication.setOverrideCursor(Qt.SplitVCursor)

            j = self.dragging_row
            dy = y_img - self.drag_start_pos[1]

            h_top = self.table.row_heights[j]
            h_bottom = self.table.row_heights[j + 1]

            dy = max(dy, -(h_top - 15))
            dy = min(dy, (h_bottom - 15))

            if abs(dy) > 0:
                self.table.row_heights[j] += dy
                self.table.row_heights[j + 1] -= dy
                self.drag_start_pos = (x_img, y_img)
                self.update()
                self.update_cells()

            return

        # --- Select multi cell ---
        if self.dragging_selection and self.drag_start_pos is not None:
            x0, y0 = self.drag_start_pos
            x1, y1 = x_img, y_img

            rect = (x0, y0, x1, y1)
            self.selected_cells = [{"position": c["position"]} for c in self.table.get_cells_in(rect)]

            self.update()

        if (
                self.hover_col is None
                and self.hover_row is None
                and self.dragging_col is None
                and self.dragging_row is None
        ):
            QApplication.restoreOverrideCursor()

    def mouseReleaseEvent(self, event):
        if not self.edit_enabled:
            return super().mouseReleaseEvent(event)

        p = event.pos()
        x_img, y_img = p.x(), p.y()

        self.dragging_col = None
        self.dragging_row = None

        # --- Stop selecting ---
        if self.dragging_selection:
            self.dragging_selection = False
            start_x, start_y = self.drag_start_pos

            if abs(x_img - start_x) < 3 and abs(y_img - start_y) < 3:
                cell = self.table.get_cell_at((x_img, y_img))
                self.selected_cells = [{"position": cell["position"]}] if cell else []

        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None

        QApplication.restoreOverrideCursor()
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

        for (r, c, rs, cs) in self.table.merged_cells:
            if (
                    r == min_row
                    and c == min_col
                    and rs == num_rows
                    and cs == num_cols
            ):
                selected_is_merged = True
                break

        selected_is_row = (
                min_col == 0 and
                max_col == self.table.cols - 1
        )

        selected_is_col = (
                min_row == 0 and
                max_row == self.table.rows - 1
        )

        if selected_is_merged:
            actions["Unmerge cells"] = menu.addAction("Unmerge cells")
        elif num_rows > 1 or num_cols > 1:
            actions["Merge cells"] = menu.addAction("Merge cells")

        if selected_is_row:
            if num_rows == 1:
                split_row_menu = menu.addMenu("Split row into")
                for n in range(2, 11):
                    act = split_row_menu.addAction(f"{n} rows")
                    act.triggered.connect(lambda checked, x=n: self.split_row(x))
            else:
                actions["Merge rows"] = menu.addAction("Merge rows")

        if selected_is_col:
            if num_cols == 1:
                split_col_menu = menu.addMenu("Split column into")
                for n in range(2, 11):
                    act = split_col_menu.addAction(f"{n} columns")
                    act.triggered.connect(lambda checked, x=n: self.split_col(x))
            else:
                actions["Merge cols"] = menu.addAction("Merge cols")

        global_pos = QCursor.pos()
        action = menu.exec_(global_pos)

        if action:
            if action == actions.get("Merge cells"):
                self.merge_selected_cells()
            elif action == actions.get("Unmerge cells"):
                self.unmerge_selected_cells()
            elif action == actions.get("Merge rows"):
                self.merge_selected_rows()
            elif action == actions.get("Merge cols"):
                self.merge_selected_cols()

    def leaveEvent(self, event):
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self.edit_enabled = False
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            return

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control and not event.isAutoRepeat():
            self.edit_enabled = True
            QApplication.restoreOverrideCursor()
            return

    # ----------------------- Rendering -----------------------
    def paintEvent(self, e):
        if not self.background_pixmap:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.drawPixmap(0, 0, self.background_pixmap)

        if not self.table:
            return

        rows = len(self.table.row_heights)
        cols = len(self.table.col_widths)

        if rows == 0 or cols == 0:
            return

        def px(v: float) -> float:
            return round(v) + 0.5

        def draw_line(x1, y1, x2, y2):
            p.drawLine(
                QPointF(px(x1), px(y1)),
                QPointF(px(x2), px(y2))
            )

        x = self.table.get_col_x_positions()
        y = self.table.get_row_y_positions()

        max_x = x[-1] - 1
        max_y = y[-1] - 1

        x[-1] = max_x
        y[-1] = max_y

        drawn = set()

        pen = QPen(Qt.green, 2)
        pen.setCosmetic(True)
        p.setPen(pen)

        # Merge cells
        for r, c, rs, cs in self.table.merged_cells:
            x1, y1 = x[c], y[r]
            x2, y2 = x[c + cs], y[r + rs]

            draw_line(x1, y1, x2, y1)  # top
            draw_line(x2, y1, x2, y2)  # right
            draw_line(x2, y2, x1, y2)  # bottom
            draw_line(x1, y2, x1, y1)  # left

            for i in range(r, r + rs):
                for j in range(c, c + cs):
                    drawn.add((i, j))

        # Single cells
        for r in range(rows):
            for c in range(cols):
                if (r, c) in drawn:
                    continue

                x1, y1 = x[c], y[r]
                x2, y2 = x[c + 1], y[r + 1]

                draw_line(x1, y1, x2, y1)
                draw_line(x2, y1, x2, y2)
                draw_line(x2, y2, x1, y2)
                draw_line(x1, y2, x1, y1)

        # Selection
        if self.selected_cells:
            r0, r1, c0, c1 = self.get_selected_bound()

            col_pos = [0]
            for w in self.table.col_widths:
                col_pos.append(col_pos[-1] + w)

            row_pos = [0]
            for h in self.table.row_heights:
                row_pos.append(row_pos[-1] + h)

            x0 = col_pos[c0]
            x1 = col_pos[c1 + 1]
            y0 = row_pos[r0]
            y1 = row_pos[r1 + 1]

            rect = QRectF(
                px(x0),
                px(y0),
                px(x1) - px(x0),
                px(y1) - px(y0)
            )

            # mask
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(100, 100, 100, 60))
            p.drawRect(rect)
            p.restore()

            # border
            pen = QPen(Qt.red, 3, Qt.DashLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect)

