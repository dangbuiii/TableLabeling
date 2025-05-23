import os
import json

def compute_overlap_ratio(text_box, cell_box):
    xA = max(text_box[0], cell_box[0])
    yA = max(text_box[1], cell_box[1])
    xB = min(text_box[2], cell_box[2])
    yB = min(text_box[3], cell_box[3])

    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH

    if interArea == 0:
        return 0.0

    textArea = (text_box[2] - text_box[0]) * (text_box[3] - text_box[1])
    if textArea == 0:
        return 0.0

    return interArea / textArea

# Thư mục
json_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\label'
txt_folder = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\OCR'
output_folder1 = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\new label 1'  # Full Box
output_folder2 = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\new label 2'  # Content Box
output_folder3 = 'F:\\Data\\detected_tables\\All table\\10-5\\1000\\new label 3'  # Average Box

# Tạo thư mục nếu chưa tồn tại
for folder in [output_folder1, output_folder2, output_folder3]:
    os.makedirs(folder, exist_ok=True)

for filename in os.listdir(json_folder):
    if not filename.endswith('.json'):
        continue

    json_path = os.path.join(json_folder, filename)
    txt_path = os.path.join(txt_folder, os.path.splitext(filename)[0] + '.txt')

    if not os.path.exists(txt_path):
        print(f"⚠ Thiếu file txt cho {filename}")
        continue

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cell_boxes = [cell['bbox'] for cell in data['cells']]
    assigned_texts = [[] for _ in range(len(cell_boxes))]

    with open(txt_path, 'r', encoding='utf-8') as f:
        text_boxes = [list(map(int, line.strip().split(','))) for line in f if line.strip()]

    # Tạo bản sao cho từng kiểu box
    data_full = json.loads(json.dumps(data))      # full box (copy gốc)
    data_content = json.loads(json.dumps(data))   # content box
    data_avg = json.loads(json.dumps(data))       # average box

    for i, cbox in enumerate(cell_boxes):
        for tbox in text_boxes:
            iou = compute_overlap_ratio(tbox, cbox)
            if iou > 0.30:
                assigned_texts[i].append(tbox)

    for i, cell in enumerate(data['cells']):
        original_box = cell['bbox']
        texts = assigned_texts[i]

        # --- FULL BOX ---
        full_cell = data_full['cells'][i]
        if texts:
            full_cell['bbox'] = original_box
            full_cell['token'] = 'temp'
        else:
            full_cell['bbox'] = [0, 0, 0, 0]
            full_cell['token'] = ''

        # --- CONTENT BOX ---
        content_cell = data_content['cells'][i]
        if texts:
            x1 = max(original_box[0], min(box[0] for box in texts))
            y1 = max(original_box[1], min(box[1] for box in texts))
            x2 = min(original_box[2], max(box[2] for box in texts))
            y2 = min(original_box[3], max(box[3] for box in texts))
            content_cell['bbox'] = [x1, y1, x2, y2]
            content_cell['token'] = 'temp'
        else:
            content_cell['bbox'] = [0, 0, 0, 0]
            content_cell['token'] = ''

        # --- AVERAGE BOX ---
        avg_cell = data_avg['cells'][i]
        box1 = full_cell['bbox']
        box2 = content_cell['bbox']
        avg_box = [
            int((box1[0] + box2[0]) / 2),
            int((box1[1] + box2[1]) / 2),
            int((box1[2] + box2[2]) / 2),
            int((box1[3] + box2[3]) / 2),
        ]
        avg_cell['bbox'] = avg_box
        avg_cell['token'] = 'temp' if texts else ''

    # Lưu các file
    with open(os.path.join(output_folder1, filename), 'w', encoding='utf-8') as f:
        json.dump(data_full, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_folder2, filename), 'w', encoding='utf-8') as f:
        json.dump(data_content, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_folder3, filename), 'w', encoding='utf-8') as f:
        json.dump(data_avg, f, ensure_ascii=False, indent=2)

    print(f"✔ Đã xử lý {filename} → 3 file (full, content, average)")
