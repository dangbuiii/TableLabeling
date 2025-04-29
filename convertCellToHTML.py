import json
from collections import defaultdict

def convert_label_to_html(label_data):
    cells = label_data['cells']
    header_start, header_end = label_data.get('header', [])[0], label_data.get('header', [])[1]
    header_rows = set(range(header_start, header_end + 1))

    # Tìm số hàng lớn nhất
    max_row = max(cell["position"][1] for cell in cells)

    # Gom các ô theo hàng bắt đầu
    rows = defaultdict(list)
    for cell in cells:
        row_start = cell["position"][0]
        rows[row_start].append(cell)

    html_rows = []

    for row in range(max_row + 1):
        if row not in rows:
            continue

        html_row = "<tr>"

        # Sắp xếp cell theo col_start để đảm bảo thứ tự
        sorted_cells = sorted(rows[row], key=lambda c: c["position"][2])
        for cell in sorted_cells:
            row_start, row_end, col_start, col_end = cell["position"]
            colspan = col_end - col_start + 1
            rowspan = row_end - row_start + 1

            # Chỉ xử lý nếu ô bắt đầu ở hàng hiện tại (tránh vẽ lại ô đã merge)
            if row != row_start:
                continue

            # Nội dung ô
            text = "TEMP" if not cell["token"] else " ".join(cell["token"])

            td_tag = "<td"
            if rowspan > 1:
                td_tag += f' rowspan=\\"{rowspan}\\"'
            if colspan > 1:
                td_tag += f' colspan=\\"{colspan}\\"'
            td_tag += f">{text}</td>"

            html_row += td_tag

        html_row += "</tr>"
        html_rows.append((row, html_row))

    # Ghép header và body
    thead_html = "".join(html for row, html in html_rows if row in header_rows)
    tbody_html = "".join(html for row, html in html_rows if row not in header_rows)

    final_html = f"<table><thead>{thead_html}</thead><tbody>{tbody_html}</tbody></table>"
    return final_html

import os

folder_path = "D:/working/KSE/OCR_Tax_Tables/datasets/data_HoaDonTaiChinhVN/Dang/phase_1/BC_TaiChinh/"  # Thay bằng đường dẫn đến folder của bạn

for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        filepath = os.path.join(folder_path, filename)
        print(filepath)
        
        # Tách tên file (không bao gồm .json)
        name = os.path.splitext(filename)[0]

        with open(filepath, 'r') as f:
            data = json.load(f)
        html = convert_label_to_html(data)
        print(f"{folder_path}{name}.html")
        with open(f"{folder_path}{name}.html", "w", encoding="utf-8") as file:
            file.write(html)
