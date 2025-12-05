import cv2
import os
import xml.etree.ElementTree as ET
from PIL import Image
from table_transformer import TableExtractionPipeline


# ============================================================
#                   LOAD MODEL CHỈ 1 LẦN
# ============================================================
pipe = TableExtractionPipeline(
    det_device="cpu",
    str_device="cpu",
    det_model_path=None,
    str_model_path="./model/model_3.pth"
)


# ============================================================
#        HÀM TIỀN XỬ LÝ: LOẠI BỎ BOX LÉP (width/height < 5)
# ============================================================
def filter_small_boxes(objects, min_size=5):
    """Loại bỏ box có width hoặc height < min_size."""
    filtered = []
    for obj in objects:
        xmin, ymin, xmax, ymax = map(int, obj["bbox"])
        w = xmax - xmin
        h = ymax - ymin
        if w >= min_size and h >= min_size:
            filtered.append(obj)
    return filtered

def overlap_small(boxA, boxB):
    """
    Trả về tỉ lệ:
        (diện tích giao nhau) / (diện tích box nhỏ hơn)
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter <= 0:
        return 0.0

    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    small_area = min(areaA, areaB)
    return inter / small_area

def filter_contained_boxes(objects, overlap_thresh=0.9):
    """
    Loại bỏ box bị lọt vào trong box khác cùng label,
    dựa trên tỷ lệ diện tích giao / diện tích box nhỏ.
    """
    keep = []
    removed_idx = set()

    for i in range(len(objects)):
        if i in removed_idx:
            continue

        box_i = list(map(int, objects[i]["bbox"]))
        label_i = objects[i]["label"]

        for j in range(len(objects)):
            if i == j or j in removed_idx:
                continue

            box_j = list(map(int, objects[j]["bbox"]))
            label_j = objects[j]["label"]

            if label_i != label_j:
                continue

            ov = overlap_small(box_i, box_j)

            # Box_i nằm trong box_j
            if ov >= overlap_thresh:
                # Loại box nhỏ hơn
                area_i = (box_i[2]-box_i[0]) * (box_i[3]-box_i[1])
                area_j = (box_j[2]-box_j[0]) * (box_j[3]-box_j[1])

                if area_i <= area_j:
                    removed_idx.add(i)
                    break    # i bị loại → xét box tiếp theo
                else:
                    removed_idx.add(j)
                    continue

        if i not in removed_idx:
            keep.append(objects[i])

    return keep




# ============================================================
#            HÀM XỬ LÝ 1 ẢNH → LƯU XML RA FILE
# ============================================================
def process_single_image(image_path: str, xml_output_folder: str):
    """Chạy TATR cho một ảnh và lưu file XML vào folder output."""

    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        return

    # Đảm bảo folder output tồn tại
    os.makedirs(xml_output_folder, exist_ok=True)

    # Load image
    img_cv = cv2.imread(image_path)
    h, w, d = img_cv.shape

    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)

    # Run inference
    result = pipe.recognize(img_pil, out_objects=True)

    # Lọc box nhỏ
    objects = filter_small_boxes(result["objects"], min_size=5)
    objects = filter_contained_boxes(objects)

    # ===========================================
    #      TẠO XML PASCAL VOC
    # ===========================================
    filename = os.path.basename(image_path)
    xml_name = os.path.splitext(filename)[0] + ".xml"
    xml_output_path = os.path.join(xml_output_folder, xml_name)

    xml_root = ET.Element("annotation")
    ET.SubElement(xml_root, "folder").text = ""
    ET.SubElement(xml_root, "filename").text = filename
    ET.SubElement(xml_root, "path").text = filename

    source = ET.SubElement(xml_root, "source")
    ET.SubElement(source, "database").text = "VietFin"

    size = ET.SubElement(xml_root, "size")
    ET.SubElement(size, "width").text = str(w)
    ET.SubElement(size, "height").text = str(h)
    ET.SubElement(size, "depth").text = str(d)

    ET.SubElement(xml_root, "segmented").text = "0"

    # Ghi object box vào XML
    for obj in objects:
        if obj["score"] < 0.8:
            continue

        label = obj["label"]
        xmin, ymin, xmax, ymax = map(int, obj["bbox"])

        obj_xml = ET.SubElement(xml_root, "object")

        ET.SubElement(obj_xml, "name").text = label
        ET.SubElement(obj_xml, "pose").text = "Frontal"
        ET.SubElement(obj_xml, "truncated").text = "0"
        ET.SubElement(obj_xml, "difficult").text = "0"
        ET.SubElement(obj_xml, "occluded").text = "0"

        bbox = ET.SubElement(obj_xml, "bndbox")
        ET.SubElement(bbox, "xmin").text = str(xmin)
        ET.SubElement(bbox, "ymin").text = str(ymin)
        ET.SubElement(bbox, "xmax").text = str(xmax)
        ET.SubElement(bbox, "ymax").text = str(ymax)

    # Save XML
    xml_tree = ET.ElementTree(xml_root)
    ET.indent(xml_tree, space="  ", level=0)
    xml_tree.write(xml_output_path, encoding="utf-8", xml_declaration=False)

    print(f"[OK] Saved XML: {xml_output_path}")


# ============================================================
#         HÀM XỬ LÝ CẢ FOLDER ẢNH → FOLDER XML
# ============================================================
def process_folder(image_folder: str, label_folder: str):

    os.makedirs(label_folder, exist_ok=True)

    for filename in os.listdir(image_folder):

        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        print(f"\n=== Processing: {filename} ===")

        img_path = os.path.join(image_folder, filename)
        xml_name = os.path.splitext(filename)[0] + ".xml"

        process_single_image(img_path, label_folder)

    print("\n=== DONE FOLDER ===")

