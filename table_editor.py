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
        self.scale_factor = 1.0
        self.parent_scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Table state
        self.rect = QRectF(0, 0, 800, 600)
        self.rows = 0
        self.cols = 0
        self.col_widths = []
        self.row_heights = []
        self.merged_cells = set()
        self.show_table = True

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
        self.rect = QRectF(0, 0, self.background_pixmap.width(), self.background_pixmap.height())

        if self.parent() and hasattr(self.parent(), "viewport"):
            viewport_size = self.parent().viewport().size()
        else:
            viewport_size = self.size()

        if not viewport_size.isEmpty():
            scale_w = viewport_size.width() / self.background_pixmap.width()
            scale_h = viewport_size.height() / self.background_pixmap.height()
            padding_ratio = 0.9  # hoặc 0.95 tùy độ padding bạn muốn
            self.scale_factor = padding_ratio * min(scale_w, scale_h)
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

        # --- Cập nhật merged_cells ---
        updated = set()
        for (r0, c0, rs, cs) in list(self.merged_cells):

            # 1. Nếu merge cell nằm hoàn toàn dưới vùng gộp -> dịch chuyển r0 lên
            if r0 > max_row:
                new_r0 = r0 - count_deleted
                updated.add((new_r0, c0, rs, cs))
                continue

            # 2. Nếu merge cell nằm hoàn toàn trên vùng gộp -> giữ nguyên
            if r0 + rs - 1 < min_row:
                updated.add((r0, c0, rs, cs))
                continue

            # 3. Nếu merge cell giao với vùng gộp
            new_r0 = r0
            new_rs = rs

            # 3a. Nếu r0 nằm dưới min_row → bị kéo lên
            if r0 > min_row:
                new_r0 = min_row

            # 3b. Tính lại chiều cao rs sau khi các hàng bị xóa
            # tính phần phía trên min_row = max(0, min_row - r0)
            above = max(0, min_row - r0)

            # tính phần nằm trong vùng bị xóa
            inside = max(0, min(rs - above, count_deleted))

            new_rs = rs - inside

            # nếu merge cell vượt xuống dưới max_row -> trừ tiếp phần bị xóa
            if r0 + rs - 1 > max_row:
                new_rs -= (r0 + rs - 1 - max_row)

            # 3c. Nếu không còn là ô merge -> bỏ
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

        # --- Cập nhật merged_cells ---
        updated = set()
        for (r0, c0, rs, cs) in list(self.merged_cells):

            # 1. Nếu merge cell nằm hoàn toàn bên phải -> dịch c0 sang trái
            if c0 > max_col:
                new_c0 = c0 - count_deleted
                updated.add((r0, new_c0, rs, cs))
                continue

            # 2. Nếu merge cell nằm hoàn toàn bên trái -> giữ nguyên
            if c0 + cs - 1 < min_col:
                updated.add((r0, c0, rs, cs))
                continue

            # 3. Nếu merge cell giao với vùng merge
            new_c0 = c0
            new_cs = cs

            # 3a. Nếu c0 nằm bên phải min_col → kéo về min_col
            if c0 > min_col:
                new_c0 = min_col

            # 3b. Tính phần nằm bên trái vùng merge
            left = max(0, min_col - c0)

            # 3c. phần merge cell nằm trong vùng xóa
            inside = max(0, min(cs - left, count_deleted))

            new_cs = cs - inside

            # 3d. Nếu merge cell vượt qua max_col → trừ tiếp
            if c0 + cs - 1 > max_col:
                new_cs -= (c0 + cs - 1 - max_col)

            # 3e. Nếu không còn là ô merge → bỏ
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

            # 1. merge-cell nằm hoàn toàn trên row split → giữ nguyên
            if r2 < selected_row:
                new_merge.add((r0, c0, rs, cs))
                continue

            # 2. merge-cell nằm hoàn toàn dưới → dịch r0
            if r0 > selected_row:
                new_merge.add((r0 + (n - 1), c0, rs, cs))
                continue

            # 3. merge-cell giao row split → mở rộng rowspan
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

        # --- Cập nhật kích thước cột ---
        total_width = self.col_widths[selected_col]
        new_width = total_width / n
        self.col_widths[selected_col] = new_width

        for i in range(1, n):
            self.col_widths.insert(selected_col + i, new_width)

        self.cols += n - 1

        # --- Cập nhật merge cell ---
        new_merge = set()

        for (r0, c0, rs, cs) in self.merged_cells:
            c1 = c0
            c2 = c0 + cs - 1

            # 1. merge-cell nằm hoàn toàn bên trái cột split → giữ nguyên
            if c2 < selected_col:
                new_merge.add((r0, c0, rs, cs))
                continue

            # 2. merge-cell nằm hoàn toàn bên phải cột split → dời sang phải
            if c0 > selected_col:
                new_merge.add((r0, c0 + (n - 1), rs, cs))
                continue

            # 3. merge-cell giao cột split → mở rộng colspan
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
        merged_cells_boxes = []  # <-- đổi tên rõ ràng

        # 1) Đọc tất cả đối tượng trong XML
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

            elif name == "table spanning cell":  # merged cell
                merged_cells_boxes.append(box)

        # Sắp xếp để đảm bảo đúng thứ tự
        rows.sort(key=lambda x: x[0])
        cols.sort(key=lambda x: x[0])

        self.rows = len(rows)
        self.cols = len(cols)

        # -----------------------
        # 2) Tìm vị trí row/col của từng spanning (merged) cell
        # -----------------------
        def find_span(cell):
            cx0, cy0, cx1, cy1 = cell

            # ----- Row start: tìm row có ry0 gần với cy0 -----
            min_dist = float('inf')
            r0 = None
            for i, (ry0, ry1) in enumerate(rows):
                dist = abs(cy0 - ry0)
                if dist < min_dist:
                    min_dist = dist
                    r0 = i

            # ----- Row end: tìm row có ry1 gần với cy1 -----
            min_dist = float('inf')
            r1 = None
            for i, (ry0, ry1) in enumerate(rows):
                dist = abs(cy1 - ry1)
                if dist < min_dist:
                    min_dist = dist
                    r1 = i

            # ----- Col start: tìm col có cx0_ gần với cx0 -----
            min_dist = float('inf')
            c0 = None
            for j, (cx0_, cx1_) in enumerate(cols):
                dist = abs(cx0 - cx0_)
                if dist < min_dist:
                    min_dist = dist
                    c0 = j

            # ----- Col end: tìm col có cx1_ gần với cx1 -----
            min_dist = float('inf')
            c1 = None
            for j, (cx0_, cx1_) in enumerate(cols):
                dist = abs(cx1 - cx1_)
                if dist < min_dist:
                    min_dist = dist
                    c1 = j

            return r0, r1, c0, c1

        # -----------------------
        # 3) Tạo danh sách span_cells (danh sách ô có span)
        # -----------------------
        # KHÔNG để max_w, max_h bị ảnh hưởng bởi merged cells
        max_w = cols[-1][1]  # chiều rộng grid
        max_h = rows[-1][1]  # chiều cao grid

        # vẫn tạo span_cells như bình thường
        span_cells = []
        for box in merged_cells_boxes:
            r0, r1, c0, c1 = find_span(box)
            if r0 is None or c0 is None:
                continue
            span_cells.append({
                "bbox": box,
                "position": [r0, r1, c0, c1],
                "token": [""]
            })

        # -----------------------
        # 4) Xây dựng col_widths & row_heights
        # -----------------------
        col_positions = [c[0] for c in cols] + [cols[-1][1]]
        row_positions = [r[0] for r in rows] + [rows[-1][1]]

        img_w = self.background_pixmap.width()
        img_h = self.background_pixmap.height()

        scale_x = img_w / max_w if max_w > 0 else 1
        scale_y = img_h / max_h if max_h > 0 else 1

        self.col_widths = [(col_positions[i + 1] - col_positions[i]) * scale_x
                           for i in range(self.cols)]
        self.row_heights = [(row_positions[j + 1] - row_positions[j]) * scale_y
                            for j in range(self.rows)]

        # -----------------------
        # 5) Gán merged cells vào bảng
        # -----------------------
        for cell in span_cells:
            r0, r1, c0, c1 = cell["position"]

            # Nếu cell chiếm nhiều hàng hoặc nhiều cột => merged cell
            if r1 > r0 or c1 > c0:
                self.merged_cells.add((r0, c0, r1 - r0 + 1, c1 - c0 + 1))

        self.update()
        self.update_cells()

        print("✅ Imported XML structure:", filename)

    def export_cells(self, filename):
        """
        Export current table to an XML format compatible with the import function:
        - one 'table' object (full image)
        - many 'table row' objects (xmin=0, xmax=img_w)
        - many 'table column' objects (ymin=0, ymax=img_h)
        - many 'table spanning cell' objects (only bndbox)
        All coordinates are in image pixel space (using self.col_widths/self.row_heights).
        """
        if self.rows == 0 or self.cols == 0:
            print("Chưa có bảng để xuất.")
            return

        # --- build cumulative positions in pixel space ---
        # col_widths and row_heights are expected to be in image pixels (as in import)
        col_positions = [0.0]
        for w in self.col_widths:
            col_positions.append(col_positions[-1] + w)
        row_positions = [0.0]
        for h in self.row_heights:
            row_positions.append(row_positions[-1] + h)

        # round to int for XML coordinates
        col_positions = [int(round(x)) for x in col_positions]
        row_positions = [int(round(y)) for y in row_positions]

        img_w = int(round(col_positions[-1]))
        img_h = int(round(row_positions[-1]))

        # --- prepare mapping of merged regions ---
        # self.merged_cells expected items: (r0, c0, rowspan, colspan)
        merged_map = {}  # key = (r0,c0) -> (rowspan, colspan)
        for m in getattr(self, "merged_cells", set()):
            try:
                r0, c0, rowspan, colspan = m
                merged_map[(r0, c0)] = (rowspan, colspan)
            except Exception:
                # if stored differently, ignore
                continue

        # We'll iterate grid left-to-right, top-to-bottom, and when we encounter
        # the top-left of a merged region we'll emit one spanning cell and skip covered cells.
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

        # minimal metadata: filename/path/size if available
        # filename
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

        print(f"✅ Successfully exported XML file: {filename}")

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
            if abs(x_img - col_lines[i]) < 1 + 1 / (self.scale_factor * self.parent_scale_factor) and self.rect.top() < y_img < self.rect.bottom():
                self.dragging_col = i - 1
                return

        # --- Check horizontal line ---
        for j in range(1, len(row_lines) - 1):
            if abs(y_img - row_lines[j]) < 1 + 1 / (self.scale_factor * self.parent_scale_factor) and self.rect.left() < x_img < self.rect.right():
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
            if abs(x_img - x_line) < 1 + 1 / (self.scale_factor * self.parent_scale_factor):
                QApplication.setOverrideCursor(Qt.SplitHCursor)
                hovering = True
                break
        if not hovering:
            for y_line in self.get_row_y_positions()[1:-1]:
                if abs(y_img - y_line) < 1 + 1 / (self.scale_factor * self.parent_scale_factor):
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

        # --- Merge cells ---
        p.setPen(QPen(Qt.green, 2))
        for r, c, rs, cs in self.merged_cells:
            x1, y1 = x[c], y[r]
            x2, y2 = x[c + cs], y[r + rs]

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
