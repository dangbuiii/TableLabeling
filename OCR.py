import os
import cv2
import numpy as np
from paddleocr import PaddleOCR

# Thư mục ảnh đầu vào và thư mục lưu file txt
input_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\image'
output_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\OCR'

# Tạo thư mục nếu chưa tồn tại
os.makedirs(output_folder, exist_ok=True)

# Khởi tạo OCR
ocr = PaddleOCR(use_angle_cls=True, lang='vi')

# Duyệt từng ảnh trong thư mục
for filename in os.listdir(input_folder):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        # Tạo tên file txt tương ứng
        txt_filename = os.path.splitext(filename)[0] + '.txt'
        txt_path = os.path.join(output_folder, txt_filename)

        # Nếu file txt đã tồn tại thì bỏ qua
        if os.path.exists(txt_path):
            print(f"⏩ Bỏ qua {filename} vì đã có {txt_filename}")
            continue

        # Đường dẫn ảnh
        image_path = os.path.join(input_folder, filename)

        # Thực hiện OCR
        results = ocr.ocr(image_path, cls=True)

        # Ghi kết quả ra file txt
        with open(txt_path, 'w', encoding='utf-8') as f:
            for line in results[0]:
                box = line[0]  # polygon 4 điểm
                text = line[1][0].strip()  # lấy text và loại bỏ khoảng trắng đầu/cuối

                # Bỏ qua nếu text có độ dài <= 1
                if len(text) <= 1 and not text.isalnum():
                    continue

                # Tính bounding box chữ nhật
                xs = [int(pt[0]) for pt in box]
                ys = [int(pt[1]) for pt in box]
                x_min, y_min = min(xs), min(ys)
                x_max, y_max = max(xs), max(ys)

                # Ghi box ra file (chỉ 4 số, ngăn cách bằng dấu phẩy)
                f.write(f"{x_min},{y_min},{x_max},{y_max}\n")

        print(f"✔ Đã xử lý {filename} → {txt_filename}")
