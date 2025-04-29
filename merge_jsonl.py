import os
import json
import convertHTMLtoToken
# from bs4 import BeautifulSoup

def generate_jsonl(dir, output_file):
    # Lấy danh sách các file JSON và HTML
    json_files = [f for f in os.listdir(dir) if f.endswith(".json")]
    # html_files = [f for f in os.listdir(dir) if f.endswith(".html")]
    with open(output_file, "w", encoding="utf-8") as outfile:
        for json_file in json_files:
            line = {"filename":"", "html":{"cells":[],"structure":{}}}
            # Tên file không bao gồm phần mở rộng
            filename_base = os.path.splitext(json_file)[0]
            line["filename"] = filename_base+ ".jpg"

            # Đọc file JSON chứa bounding box
            with open(os.path.join(dir, json_file), "r", encoding="utf-8") as json_f:
                json_data = json.load(json_f)
                for i in range (len(json_data["cells"])):
                    line["html"]["cell"].append({"tokens":[], "bbox":json_data["cells"][i]["bbox"]})


            # Đọc file HTML tương ứng
            html_token = convertHTMLtoToken.html_to_token_structure(os.path.join(dir, f"{filename_base}.html"))
            line["html"]["structure"] = html_token

            # Ghi dữ liệu vào file JSONL
            json.dump(line, outfile, ensure_ascii=False)
            outfile.write("\n")

json_dir = "D:\\working\\KSE\\OCR_Tax_Tables\\datasets\\data_HoaDonTaiChinhVN\\Dang\\phase_1\\BC_TaiChinh"  # Đường dẫn tới thư mục chứa file JSON
output_file = "output.jsonl"  # Tên file JSONL đầu ra

generate_jsonl(json_dir, output_file)

