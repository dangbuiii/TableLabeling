import os
import json
import cv2

# Đường dẫn
json_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\50\\label'
txt_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\50\\OCR'
image_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\50\\image'

for filename in os.listdir(json_folder):
    if not filename.endswith('.json'):
        continue

    json_path = os.path.join(json_folder, filename)
    txt_path = os.path.join(txt_folder, os.path.splitext(filename)[0] + '.txt')
    image_path = os.path.join(image_folder, os.path.splitext(filename)[0] + '.jpg')  # hoặc .png

    if not os.path.exists(txt_path) or not os.path.exists(image_path):
        print(f"⚠ Thiếu file txt hoặc ảnh cho {filename}")
        continue

    image = cv2.imread(image_path)
    if image is None:
        print(f"⚠ Không thể đọc ảnh {image_path}")
        continue

    # Đọc bounding boxes từ JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for cell in data['cells']:
        x1, y1, x2, y2 = cell['bbox']
        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Xanh dương
        cv2.putText(image, 'cell', (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    # Đọc text boxes từ TXT
    with open(txt_path, 'r', encoding='utf-8') as f:
        text_boxes = [list(map(int, line.strip().split(','))) for line in f if line.strip()]
    for box in text_boxes:
        x1, y1, x2, y2 = box
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Đỏ
        cv2.putText(image, 'txt', (x1, y2 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    # Hiển thị ảnh
    cv2.imshow('Image with boxes', image)
    key = cv2.waitKey(0)
    if key == 27:  # Nhấn ESC để thoát sớm
        break

cv2.destroyAllWindows()
