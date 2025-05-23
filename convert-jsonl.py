import os
import json
from collections import defaultdict


def convert_json_to_token_structure(label_data):
    tokens = []

    cells = label_data["cells"]
    header_start, header_end = label_data.get("header", [0, -1])
    header_rows = set(range(header_start, header_end + 1))
    max_row = max(cell["position"][1] for cell in cells)

    rows = defaultdict(list)
    for cell in cells:
        row_start = cell["position"][0]
        rows[row_start].append(cell)

    tokens.append("<table>")

    def build_section(row_indices, section_name):
        tokens.append(f"<{section_name}>")
        for row in sorted(row_indices):
            if row not in rows:
                continue
            tokens.append("<tr>")
            sorted_cells = sorted(rows[row], key=lambda c: c["position"][2])
            for cell in sorted_cells:
                row_start, row_end, col_start, col_end = cell["position"]
                if row != row_start:
                    continue  # tránh duplicate nếu là merge từ trên xuống

                attr_str = ""
                if (row_end - row_start + 1) > 1:
                    attr_str += f' rowspan="{row_end - row_start + 1}"'
                if (col_end - col_start + 1) > 1:
                    attr_str += f' colspan="{col_end - col_start + 1}"'
                tokens.append(f"<td{attr_str}>")
                tokens.append("</td>")
            tokens.append("</tr>")
        tokens.append(f"</{section_name}>")

    build_section(header_rows, "thead")
    build_section([r for r in rows if r not in header_rows], "tbody")
    tokens.append("</table>")

    return {"tokens": tokens}


def generate_jsonl_from_json(input_dir, output_file):
    json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]

    with open(output_file, "w", encoding="utf-8") as outfile:
        for json_file in json_files:
            filename_base = os.path.splitext(json_file)[0]
            image_filename = filename_base + ".jpg"

            # Load JSON file
            with open(os.path.join(input_dir, json_file), "r", encoding="utf-8") as f:
                label_data = json.load(f)

            line = {
                "filename": image_filename,
                "html": {
                    "cell": [],
                    "structure": {}
                }
            }

            # Add bbox info
            for cell in label_data.get("cells", []):
                token = cell.get("token", "")
                if token == "":
                    line["html"]["cell"].append({
                        "tokens": []
                    })
                else:
                    line["html"]["cell"].append({
                        "tokens": ["<b>"] + list(token) + ["</b>"],
                        "bbox": cell["bbox"]
                    })

            # Generate structure tokens from label_data directly
            token_structure = convert_json_to_token_structure(label_data)
            line["html"]["structure"] = token_structure

            json.dump(line, outfile, ensure_ascii=False)
            outfile.write("\n")


# ==== CONFIGURATION ====
input_dir = "F:\\Data\\detected_tables\\All table\\10-5\\1000\\new label 3"
output_file = "F:\\Data\\detected_tables\\All table\\10-5\\1000\\label3.jsonl"

generate_jsonl_from_json(input_dir, output_file)
