import os
import cv2
import json

# Thư mục ảnh gốc và thư mục json mới đã update box
image_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\image'
json_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\new label 3'

for filename in os.listdir(json_folder):
    if not filename.endswith('.json'):
        continue

    json_path = os.path.join(json_folder, filename)
    image_name = os.path.splitext(filename)[0] + '.jpg'  # hoặc .png, tùy định dạng ảnh
    image_path = os.path.join(image_folder, image_name)

    if not os.path.exists(image_path):
        print(f"⚠ Không tìm thấy ảnh tương ứng: {image_name}")
        continue

    # Đọc ảnh
    image = cv2.imread(image_path)

    # Đọc file JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    # Vẽ các box lên ảnh
    for cell in data.get('cells', []):
        bbox = cell.get('bbox', [])
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = map(int, bbox)
            if x_min == y_min == x_max == y_max == 0:
                continue
            count += 1
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 1)

    # Hiển thị ảnh
    cv2.imshow('Boxes on Image', image)
    print(f"Đang hiển thị: {image_name} - nhấn phím bất kỳ để tiếp tục, ESC để thoát")
    print("Box count = " + str(count))
    key = cv2.waitKey(0)
    if key == 27:  # ESC key
        break

cv2.destroyAllWindows()
