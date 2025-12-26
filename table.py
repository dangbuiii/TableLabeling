class Table:
    def __init__(self, col_widths, row_heights, merged_cells=None):
        self.col_widths = list(col_widths)
        self.row_heights = list(row_heights)

        self.cols = len(self.col_widths)
        self.rows = len(self.row_heights)

        self.merged_cells = set(merged_cells) if merged_cells else set()

    def get_col_x_positions(self):
        x = [0]
        for w in self.col_widths:
            x.append(x[-1] + w)
        return x

    def get_row_y_positions(self):
        y = [0]
        for h in self.row_heights:
            y.append(y[-1] + h)
        return y

    def get_all_cells(self):
        cells = []
        if self.rows == 0 or self.cols == 0:
            return cells

        x_positions = self.get_col_x_positions()
        y_positions = self.get_row_y_positions()

        merged_map = {(r, c): (rs, cs) for (r, c, rs, cs) in self.merged_cells}

        for r in range(self.rows):
            for c in range(self.cols):

                # merged cells
                if (r, c) in merged_map:
                    rs, cs = merged_map[(r, c)]

                # skip cells covered by merged cell
                elif any(
                        rr <= r < rr + rs and cc <= c < cc + cs
                        for (rr, cc, rs, cs) in self.merged_cells
                ):
                    continue

                # normal cell
                else:
                    rs, cs = 1, 1

                x0 = x_positions[c]
                y0 = y_positions[r]
                x1 = x_positions[c + cs]
                y1 = y_positions[r + rs]

                cells.append({
                    "bbox": [int(x0), int(y0), int(x1), int(y1)],
                    "position": [r, c, rs, cs]
                })

        return cells

    def get_cell_at(self, point):
        px, py = point

        for cell in self.get_all_cells():
            x0, y0, x1, y1 = cell["bbox"]
            if x0 <= px <= x1 and y0 <= py <= y1:
                return cell

        return None

    def get_cells_in(self, rect):
        cells = []

        rx0, ry0, rx1, ry1 = rect

        if rx0 > rx1:
            rx0, rx1 = rx1, rx0
        if ry0 > ry1:
            ry0, ry1 = ry1, ry0

        for cell in self.get_all_cells():
            x0, y0, x1, y1 = cell["bbox"]

            if (
                    x1 <= rx0 or
                    x0 >= rx1 or
                    y1 <= ry0 or
                    y0 >= ry1
            ):
                continue

            cells.append(cell)

        return cells

    def insert_row(self, index, height):
        if index < 0 or index > self.rows:
            return

        self.row_heights.insert(index, height)
        self.rows += 1

        new_merges = set()

        for (r, c, rs, cs) in self.merged_cells:
            if r >= index:
                new_merges.add((r + 1, c, rs, cs))

            elif r < index < r + rs:
                new_merges.add((r, c, rs + 1, cs))

            else:
                new_merges.add((r, c, rs, cs))

        self.merged_cells = new_merges

    def insert_col(self, index, width):
        if index < 0 or index > self.cols:
            return

        self.col_widths.insert(index, width)
        self.cols += 1

        new_merges = set()

        for (r, c, rs, cs) in self.merged_cells:
            if c >= index:
                new_merges.add((r, c + 1, rs, cs))

            elif c < index < c + cs:
                new_merges.add((r, c, rs, cs + 1))

            else:
                new_merges.add((r, c, rs, cs))

        self.merged_cells = new_merges

    def delete_row(self, index):
        if index < 0 or index >= self.rows:
            return

        self.row_heights.pop(index)
        self.rows -= 1

        new_merges = set()

        for (r, c, rs, cs) in self.merged_cells:
            if r + rs - 1 < index:
                new_merges.add((r, c, rs, cs))

            elif r > index:
                new_merges.add((r - 1, c, rs, cs))

            elif r <= index < r + rs:
                if rs > 1:
                    new_merges.add((r, c, rs - 1, cs))

        self.merged_cells = new_merges

    def delete_col(self, index):
        if index < 0 or index >= self.cols:
            return

        self.col_widths.pop(index)
        self.cols -= 1

        new_merges = set()

        for (r, c, rs, cs) in self.merged_cells:
            if c + cs - 1 < index:
                new_merges.add((r, c, rs, cs))

            elif c > index:
                new_merges.add((r, c - 1, rs, cs))

            elif c <= index < c + cs:
                if cs > 1:
                    new_merges.add((r, c, rs, cs - 1))

        self.merged_cells = new_merges

    def merge_cells(self, cells):
        if not cells or len(cells) < 2:
            return

        all_rows = []
        all_cols = []

        for cell in cells:
            r, c, rs, cs = cell["position"]
            all_rows.extend(range(r, r + rs))
            all_cols.extend(range(c, c + cs))

        min_r, max_r = min(all_rows), max(all_rows)
        min_c, max_c = min(all_cols), max(all_cols)

        rs = max_r - min_r + 1
        cs = max_c - min_c + 1

        new_merges = set()

        for (r, c, mrs, mcs) in self.merged_cells:
            intersects = not (
                    r + mrs - 1 < min_r or
                    min_r + rs - 1 < r or
                    c + mcs - 1 < min_c or
                    min_c + cs - 1 < c
            )

            if not intersects:
                new_merges.add((r, c, mrs, mcs))

        new_merges.add((min_r, min_c, rs, cs))
        self.merged_cells = new_merges

    def unmerge_cell(self, r, c):
        for merge in self.merged_cells:
            mr, mc, rs, cs = merge
            if mr <= r < mr + rs and mc <= c < mc + cs:
                self.merged_cells.remove(merge)
                return
