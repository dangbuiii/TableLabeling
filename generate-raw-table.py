import os
import json
import torch
import torchvision.transforms as T
import numpy as np
from PIL import Image
import cv2
from glob import glob

# === CẤU HÌNH ===
model_path = 'space_full_model.pth'  # đường dẫn model
input_folder = "F:\\Data\\detected_tables\\All table\\10-5\\10\\image"
output_folder = "F:\\Data\\detected_tables\\All table\\10-5\\10\\label"
os.makedirs(output_folder, exist_ok=True)

# === DEVICE ===
device = torch.device("cpu")

# === LOAD MODEL ===
model = torch.load(model_path, map_location=device)
model.to(device)
model.eval()

# === TRANSFORM ===
transform = T.Compose([
    T.ToTensor()
])

# === DỰ ĐOÁN BOX & CHUYỂN SANG GRID ===
def predict_box(image, model, transform, confidence_threshold=0.7):
    if isinstance(image, np.ndarray):
        image_pil = Image.fromarray(image)
    else:
        image_pil = image

    image_tensor = transform(image_pil).unsqueeze(0)

    with torch.no_grad():
        prediction = model(image_tensor.to(device))[0]

    output_image = np.array(image.copy()) if isinstance(image, np.ndarray) else np.array(image)

    column_lines = []
    row_lines = []

    for box, label, score in zip(prediction['boxes'], prediction['labels'], prediction['scores']):
        if score >= confidence_threshold:
            x1, y1, x2, y2 = map(int, box.cpu().numpy())
            if label == 1:  # cột
                center_x = (x1 + x2) // 2
                column_lines.append(center_x)
            elif label == 2:  # hàng
                center_y = (y1 + y2) // 2
                row_lines.append(center_y)

    column_lines.sort()
    row_lines.sort()

    h, w = output_image.shape[:2]
    x1_border, y1_border = 0, 0
    x2_border, y2_border = w, h

    column_lines.insert(0, x1_border)
    column_lines.append(x2_border)
    row_lines.insert(0, y1_border)
    row_lines.append(y2_border)

    cells = []
    for i in range(len(column_lines) - 1):
        for j in range(len(row_lines) - 1):
            x1, x2 = column_lines[i], column_lines[i+1]
            y1, y2 = row_lines[j], row_lines[j+1]
            cells.append((x1, y1, x2, y2))

    return cells, len(column_lines) - 1, len(row_lines) - 1

# === CHUYỂN ĐỔI SANG JSON ===
def export_to_json(cells, N, M, output_path):
    cell_list = []
    for idx, (x1, y1, x2, y2) in enumerate(cells):
        row = idx % M
        col = idx // M
        cell = {
            "token": [],
            "bbox": [x1, y1, x2, y2],
            "position": [row, row, col, col]
        }
        cell_list.append(cell)

    label = {
        "cells": cell_list,
        "header": [0, 0]  # giả định header là dòng đầu tiên
    }

    with open(output_path, 'w') as f:
        json.dump(label, f, indent=4)

# === XỬ LÝ TOÀN BỘ ẢNH TRONG FOLDER ===
image_paths = glob(os.path.join(input_folder, "*.jpg"))
total = len(image_paths)

for idx, img_path in enumerate(image_paths, 1):
    origin_image = cv2.imread(img_path)
    cells, N, M = predict_box(origin_image, model, transform)

    json_name = os.path.basename(img_path).replace(".jpg", ".json")
    json_path = os.path.join(output_folder, json_name)

    export_to_json(cells, N, M, json_path)
    print(f"[{idx}/{total}] ✅ Exported: {json_name}")

print("🎉 Tất cả ảnh đã được xử lý và lưu JSON.")
