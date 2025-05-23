import os
import cv2

# Đường dẫn tới thư mục ảnh và thư mục chứa file txt box
image_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\50\\image'
box_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\50\\OCR'

# Duyệt từng file ảnh
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        image_path = os.path.join(image_folder, filename)
        txt_filename = os.path.splitext(filename)[0] + '.txt'
        txt_path = os.path.join(box_folder, txt_filename)

        # Đọc ảnh
        image = cv2.imread(image_path)

        # Đọc box từ file txt nếu tồn tại
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            x_min, y_min, x_max, y_max = map(int, line.split(','))
                            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                        except ValueError:
                            print(f"Lỗi định dạng trong file: {txt_filename}, dòng: {line}")

        # Hiển thị ảnh
        cv2.imshow("OCR Box Check", image)
        print(f"Đang hiển thị: {filename} - nhấn bất kỳ phím nào để tiếp tục...")
        cv2.waitKey(0)  # Nhấn phím bất kỳ để sang ảnh tiếp theo

cv2.destroyAllWindows()
