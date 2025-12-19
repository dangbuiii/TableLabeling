from PyQt5.QtWidgets import QApplication, QWidget, QMenu
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor, QCursor
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
import xml.etree.ElementTree as ET
from xml.dom.minidom import Document


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

        # Table state
        self.rect = QRectF(0, 0, 800, 600)
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []
        self.merged_cells = set()
        self.edit_enabled = True

        # Mouse interaction
        self.dragging_col = None
        self.dragging_row = None
        self.drag_start_pos = None
        self.selected_cells = []
        self.dragging_selection = False
        self.hover_col = None
        self.hover_row = None

    # ----------------------- Utility functions -----------------------
    def map_to_image_coord(self, pt):
        return pt.x(), pt.y()

    def hit_tolerance(self):
        view = self.parent()
        if view and hasattr(view, "transform"):
            scale = view.transform().m11()
            if scale > 0:
                return max(4, 8 / scale)
        return 5

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

                cells.append({
                    "bbox": [int(x0), int(y0), int(x1), int(y1)],
                    "start_row": start_row,
                    "end_row": end_row,
                    "start_col": start_col,
                    "end_col": end_col,
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

        if self.background_pixmap.isNull():
            return

        self.setFixedSize(
            self.background_pixmap.width(),
            self.background_pixmap.height()
        )

        self.update()

    def create_table(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.col_widths = [self.rect.width() / cols] * cols
        self.row_heights = [self.rect.height() / rows] * rows
        self.merged_cells.clear()
        self.selected_cells = []
        self.update()
        self.update_cells()

    def clear_table(self):
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []
        self.merged_cells = set()
        self.selected_cells = []
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
            self.merged_cells.remove(target)

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_rows(self):
        if not self.selected_cells:
            return

        min_row, max_row, _, _ = self.get_selected_bound()
        deleted_rows = list(range(min_row + 1, max_row + 1))
        count_deleted = len(deleted_rows)

        for row_index in deleted_rows:
            self.row_heights[min_row] += self.row_heights[row_index]

        del self.row_heights[min_row + 1:max_row + 1]
        self.rows = len(self.row_heights)

        updated = set()
        for (r0, c0, rs, cs) in list(self.merged_cells):

            if r0 > max_row:
                new_r0 = r0 - count_deleted
                updated.add((new_r0, c0, rs, cs))
                continue

            if r0 + rs - 1 < min_row:
                updated.add((r0, c0, rs, cs))
                continue

            new_r0 = r0
            new_rs = rs

            if r0 > min_row:
                new_r0 = min_row

            above = max(0, min_row - r0)

            inside = max(0, min(rs - above, count_deleted))

            new_rs = rs - inside

            if r0 + rs - 1 > max_row:
                new_rs -= (r0 + rs - 1 - max_row)

            if new_rs <= 1 and cs <= 1:
                continue

            updated.add((new_r0, c0, new_rs, cs))

        self.merged_cells = updated

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def merge_selected_cols(self):
        if not self.selected_cells:
            return

        _, _, min_col, max_col = self.get_selected_bound()
        deleted_cols = list(range(min_col + 1, max_col + 1))
        count_deleted = len(deleted_cols)

        for col_index in deleted_cols:
            self.col_widths[min_col] += self.col_widths[col_index]

        del self.col_widths[min_col + 1:max_col + 1]
        self.cols = len(self.col_widths)

        updated = set()
        for (r0, c0, rs, cs) in list(self.merged_cells):

            if c0 > max_col:
                new_c0 = c0 - count_deleted
                updated.add((r0, new_c0, rs, cs))
                continue

            if c0 + cs - 1 < min_col:
                updated.add((r0, c0, rs, cs))
                continue

            new_c0 = c0
            new_cs = cs

            if c0 > min_col:
                new_c0 = min_col

            left = max(0, min_col - c0)

            inside = max(0, min(cs - left, count_deleted))

            new_cs = cs - inside

            if c0 + cs - 1 > max_col:
                new_cs -= (c0 + cs - 1 - max_col)

            if new_cs <= 1 and rs <= 1:
                continue

            updated.add((r0, new_c0, rs, new_cs))

        self.merged_cells = updated

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_row(self, n=2):
        if not self.selected_cells or n < 2:
            return

        selected_row = min(c["start_row"] for c in self.selected_cells)

        total_height = self.row_heights[selected_row]
        new_height = total_height / n
        self.row_heights[selected_row] = new_height
        for i in range(1, n):
            self.row_heights.insert(selected_row + i, new_height)

        self.rows += n - 1

        new_merge = set()

        for (r0, c0, rs, cs) in self.merged_cells:
            r1 = r0
            r2 = r0 + rs - 1

            if r2 < selected_row:
                new_merge.add((r0, c0, rs, cs))
                continue

            if r0 > selected_row:
                new_merge.add((r0 + (n - 1), c0, rs, cs))
                continue

            new_r0 = r0
            new_rs = rs + (n - 1)
            new_merge.add((new_r0, c0, new_rs, cs))

        self.merged_cells = new_merge

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def split_col(self, n=2):
        if not self.selected_cells or n < 2:
            return

        selected_col = min(c["start_col"] for c in self.selected_cells)

        total_width = self.col_widths[selected_col]
        new_width = total_width / n
        self.col_widths[selected_col] = new_width

        for i in range(1, n):
            self.col_widths.insert(selected_col + i, new_width)

        self.cols += n - 1

        new_merge = set()

        for (r0, c0, rs, cs) in self.merged_cells:
            c1 = c0
            c2 = c0 + cs - 1

            if c2 < selected_col:
                new_merge.add((r0, c0, rs, cs))
                continue

            if c0 > selected_col:
                new_merge.add((r0, c0 + (n - 1), rs, cs))
                continue

            new_c0 = c0
            new_cs = cs + (n - 1)
            new_merge.add((r0, new_c0, rs, new_cs))

        self.merged_cells = new_merge

        self.selected_cells.clear()
        self.update()
        self.update_cells()

    def import_cells(self, filename):
        self.clear_table()

        tree = ET.parse(filename)
        root = tree.getroot()

        rows = []
        cols = []
        merged_cells_boxes = []

        for obj in root.findall("object"):
            name = obj.findtext("name")
            bb = obj.find("bndbox")

            xmin = int(bb.findtext("xmin"))
            ymin = int(bb.findtext("ymin"))
            xmax = int(bb.findtext("xmax"))
            ymax = int(bb.findtext("ymax"))

            box = (xmin, ymin, xmax, ymax)

            if name == "table row":
                rows.append((ymin, ymax))

            elif name == "table column":
                cols.append((xmin, xmax))

            elif name == "table spanning cell":
                merged_cells_boxes.append(box)

        # sort
        rows.sort(key=lambda x: x[0])
        cols.sort(key=lambda x: x[0])

        self.rows = len(rows)
        self.cols = len(cols)

        if self.rows == 0 or self.cols == 0:
            print("⚠️ No rows or columns found in XML")
            return

        # normalize
        img_w = self.background_pixmap.width()
        img_h = self.background_pixmap.height()

        cols[0] = (0, cols[0][1])
        cols[-1] = (cols[-1][0], img_w)

        rows[0] = (0, rows[0][1])
        rows[-1] = (rows[-1][0], img_h)

        def find_span(cell):
            cx0, cy0, cx1, cy1 = cell

            r0 = min(range(len(rows)), key=lambda i: abs(cy0 - rows[i][0]))
            r1 = min(range(len(rows)), key=lambda i: abs(cy1 - rows[i][1]))
            c0 = min(range(len(cols)), key=lambda j: abs(cx0 - cols[j][0]))
            c1 = min(range(len(cols)), key=lambda j: abs(cx1 - cols[j][1]))

            return r0, r1, c0, c1

        span_cells = []
        for box in merged_cells_boxes:
            r0, r1, c0, c1 = find_span(box)
            span_cells.append({
                "bbox": box,
                "position": [r0, r1, c0, c1],
                "token": [""]
            })

        # calculate rows/columns size
        col_positions = []
        for i in range(len(cols)):
            col_positions.append(cols[i][0])
        col_positions.append(cols[-1][1])

        row_positions = []
        for i in range(len(rows)):
            row_positions.append(rows[i][0])
        row_positions.append(rows[-1][1])

        self.col_widths = []
        for i in range(self.cols):
            self.col_widths.append(col_positions[i + 1] - col_positions[i])

        self.row_heights = []
        for j in range(self.rows):
            self.row_heights.append(row_positions[j + 1] - row_positions[j])

        # import merge cells
        for cell in span_cells:
            r0, r1, c0, c1 = cell["position"]

            if r1 > r0 or c1 > c0:
                self.merged_cells.add(
                    (r0, c0, r1 - r0 + 1, c1 - c0 + 1)
                )

        self.update()
        self.update_cells()

        print("Imported XML structure: ", filename)

    def export_cells(self, filename):
        if self.rows == 0 or self.cols == 0:
            return

        col_positions = [0.0]
        for w in self.col_widths:
            col_positions.append(col_positions[-1] + w)
        row_positions = [0.0]
        for h in self.row_heights:
            row_positions.append(row_positions[-1] + h)

        col_positions = [int(round(x)) for x in col_positions]
        row_positions = [int(round(y)) for y in row_positions]

        img_w = int(round(col_positions[-1]))
        img_h = int(round(row_positions[-1]))

        merged_map = {}  # key = (r0,c0) -> (rowspan, colspan)
        for m in getattr(self, "merged_cells", set()):
            try:
                r0, c0, rowspan, colspan = m
                merged_map[(r0, c0)] = (rowspan, colspan)
            except Exception:
                continue

        visited = [[False] * self.cols for _ in range(self.rows)]
        span_cells_boxes = []

        for r in range(self.rows):
            for c in range(self.cols):
                if visited[r][c]:
                    continue

                if (r, c) in merged_map:
                    rowspan, colspan = merged_map[(r, c)]
                else:
                    rowspan, colspan = 1, 1

                # mark covered
                for rr in range(r, min(self.rows, r + rowspan)):
                    for cc in range(c, min(self.cols, c + colspan)):
                        visited[rr][cc] = True

                xmin = col_positions[c]
                xmax = col_positions[min(self.cols, c + colspan)]
                ymin = row_positions[r]
                ymax = row_positions[min(self.rows, r + rowspan)]

                span_cells_boxes.append((xmin, ymin, xmax, ymax))

        # --- build XML doc ---
        doc = Document()
        annotation = doc.createElement("annotation")
        doc.appendChild(annotation)

        fname_node = doc.createElement("filename")
        try:
            fname_node.appendChild(doc.createTextNode(self.image_filename))
        except Exception:
            fname_node.appendChild(doc.createTextNode(""))
        annotation.appendChild(fname_node)

        # size block
        size = doc.createElement("size")
        wn = doc.createElement("width");
        wn.appendChild(doc.createTextNode(str(img_w)));
        size.appendChild(wn)
        hn = doc.createElement("height");
        hn.appendChild(doc.createTextNode(str(img_h)));
        size.appendChild(hn)
        dn = doc.createElement("depth");
        dn.appendChild(doc.createTextNode(str(3)));
        size.appendChild(dn)
        annotation.appendChild(size)

        # 1) object: table (full image)
        obj_table = doc.createElement("object")
        name_table = doc.createElement("name");
        name_table.appendChild(doc.createTextNode("table"));
        obj_table.appendChild(name_table)
        bnd_table = doc.createElement("bndbox")
        for tag, val in zip(["xmin", "ymin", "xmax", "ymax"], [0, 0, img_w, img_h]):
            t = doc.createElement(tag);
            t.appendChild(doc.createTextNode(str(val)));
            bnd_table.appendChild(t)
        obj_table.appendChild(bnd_table)
        annotation.appendChild(obj_table)

        # 2) objects: table rows
        for (y0, y1) in zip(row_positions[:-1], row_positions[1:]):
            obj = doc.createElement("object")
            name = doc.createElement("name");
            name.appendChild(doc.createTextNode("table row"));
            obj.appendChild(name)
            bnd = doc.createElement("bndbox")
            xmin_n = doc.createElement("xmin");
            xmin_n.appendChild(doc.createTextNode(str(0)));
            bnd.appendChild(xmin_n)
            ymin_n = doc.createElement("ymin");
            ymin_n.appendChild(doc.createTextNode(str(y0)));
            bnd.appendChild(ymin_n)
            xmax_n = doc.createElement("xmax");
            xmax_n.appendChild(doc.createTextNode(str(img_w)));
            bnd.appendChild(xmax_n)
            ymax_n = doc.createElement("ymax");
            ymax_n.appendChild(doc.createTextNode(str(y1)));
            bnd.appendChild(ymax_n)
            obj.appendChild(bnd)
            annotation.appendChild(obj)

        # 3) objects: table columns
        for (x0, x1) in zip(col_positions[:-1], col_positions[1:]):
            obj = doc.createElement("object")
            name = doc.createElement("name");
            name.appendChild(doc.createTextNode("table column"));
            obj.appendChild(name)
            bnd = doc.createElement("bndbox")
            xmin_n = doc.createElement("xmin");
            xmin_n.appendChild(doc.createTextNode(str(x0)));
            bnd.appendChild(xmin_n)
            ymin_n = doc.createElement("ymin");
            ymin_n.appendChild(doc.createTextNode(str(0)));
            bnd.appendChild(ymin_n)
            xmax_n = doc.createElement("xmax");
            xmax_n.appendChild(doc.createTextNode(str(x1)));
            bnd.appendChild(xmax_n)
            ymax_n = doc.createElement("ymax");
            ymax_n.appendChild(doc.createTextNode(str(img_h)));
            bnd.appendChild(ymax_n)
            obj.appendChild(bnd)
            annotation.appendChild(obj)

        # 4) objects: table spanning cell (only bndbox)
        for (xmin, ymin, xmax, ymax) in span_cells_boxes:
            obj = doc.createElement("object")
            name = doc.createElement("name");
            name.appendChild(doc.createTextNode("table spanning cell"));
            obj.appendChild(name)
            bnd = doc.createElement("bndbox")
            for tag, val in zip(["xmin", "ymin", "xmax", "ymax"], [xmin, ymin, xmax, ymax]):
                t = doc.createElement(tag);
                t.appendChild(doc.createTextNode(str(val)));
                bnd.appendChild(t)
            obj.appendChild(bnd)
            annotation.appendChild(obj)

        # write file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent="  "))

        print(f"Successfully exported XML file: {filename}")

    # ----------------------- Event handlers -----------------------
    def mousePressEvent(self, event):
        if not self.edit_enabled or self.rows == 0 or self.cols == 0:
            return super().mousePressEvent(event)

        x_img, y_img = self.map_to_image_coord(event.pos())
        self.drag_start_pos = (x_img, y_img)
        self.dragging_col = None
        self.dragging_row = None
        self.dragging_selection = False

        col_lines = self.get_col_x_positions()
        row_lines = self.get_row_y_positions()

        tol = self.hit_tolerance()

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
        if not self.edit_enabled or self.rows == 0 or self.cols == 0:
            return super().mouseMoveEvent(event)

        x_img, y_img = self.map_to_image_coord(event.pos())

        tol = self.hit_tolerance()

        self.hover_col = None
        self.hover_row = None

        # vertical
        for i, x_line in enumerate(self.get_col_x_positions()[1:-1]):
            if abs(x_img - x_line) < tol:
                self.hover_col = i
                break

        # horizontal
        if self.hover_col is None:
            for j, y_line in enumerate(self.get_row_y_positions()[1:-1]):
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

            w_left = self.col_widths[i]
            w_right = self.col_widths[i + 1]

            dx = max(dx, -(w_left - 15))
            dx = min(dx, (w_right - 15))

            if abs(dx) > 0:
                self.col_widths[i] += dx
                self.col_widths[i + 1] -= dx
                self.drag_start_pos = (x_img, y_img)
                self.update()
                self.update_cells()

            return

        # --- drag horizontal line ---
        if self.dragging_row is not None and self.drag_start_pos is not None:
            QApplication.setOverrideCursor(Qt.SplitVCursor)

            j = self.dragging_row
            dy = y_img - self.drag_start_pos[1]

            h_top = self.row_heights[j]
            h_bottom = self.row_heights[j + 1]

            dy = max(dy, -(h_top - 15))
            dy = min(dy, (h_bottom - 15))

            if abs(dy) > 0:
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

        if event.key() == Qt.Key_Tab:
            if self.selected_cells:
                index = self.get_all_cells().index(self.selected_cells[0])
                self.select_cell((index + 1) % len(self.get_all_cells()))

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

        if self.rows == 0 or self.cols == 0:
            return

        # ---------------- Pixel helper ----------------
        def px(v: float) -> float:
            return round(v) + 0.5

        def draw_line(x1, y1, x2, y2):
            p.drawLine(
                QPointF(px(x1), px(y1)),
                QPointF(px(x2), px(y2))
            )

        # ----------------------------------------------
        x = self.get_col_x_positions()
        y = self.get_row_y_positions()

        drawn = set()

        pen = QPen(Qt.green, 2)
        pen.setCosmetic(True)
        p.setPen(pen)

        # -------- Merge cells --------
        for r, c, rs, cs in self.merged_cells:
            x1, y1 = x[c], y[r]
            x2, y2 = x[c + cs], y[r + rs]

            draw_line(x1, y1, x2, y1)  # top
            draw_line(x2, y1, x2, y2)  # right
            draw_line(x2, y2, x1, y2)  # bottom
            draw_line(x1, y2, x1, y1)  # left

            for i in range(r, r + rs):
                for j in range(c, c + cs):
                    drawn.add((i, j))

        # -------- Single cells --------
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in drawn:
                    continue

                x1, y1 = x[c], y[r]
                x2, y2 = x[c + 1], y[r + 1]

                draw_line(x1, y1, x2, y1)
                draw_line(x2, y1, x2, y2)
                draw_line(x2, y2, x1, y2)
                draw_line(x1, y2, x1, y1)

        # -------- Selection --------
        if self.selected_cells:
            min_row, max_row, min_col, max_col = self.get_selected_bound()

            x0 = x[min_col]
            y0 = y[min_row]
            x1 = x[max_col + 1]
            y1 = y[max_row + 1]

            rect = QRectF(px(x0), px(y0), px(x1) - px(x0), px(y1) - px(y0))

            # mask
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(100, 100, 100, 60))
            p.drawRect(rect)
            p.restore()

            # border
            grid_pen = QPen(Qt.red, 3, Qt.DashLine)
            grid_pen.setCosmetic(True)
            p.setPen(grid_pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect)



