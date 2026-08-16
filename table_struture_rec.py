import cv2
import os
import xml.etree.ElementTree as ET
from PIL import Image
from table_transformer import TableExtractionPipeline
from converter import boxes_to_voc_xml


def box_area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def intersection_area(a, b):
    xA = max(a[0], b[0])
    yA = max(a[1], b[1])
    xB = min(a[2], b[2])
    yB = min(a[3], b[3])
    return max(0, xB - xA) * max(0, yB - yA)


def iob(a, b):
    inter = intersection_area(a, b)
    if inter <= 0:
        return 0.0
    return inter / min(box_area(a), box_area(b))


# Basic filters
def filter_small_boxes(objects, min_size=5):
    out = []
    for o in objects:
        x1, y1, x2, y2 = map(int, o["bbox"])
        if (x2 - x1) >= min_size and (y2 - y1) >= min_size:
            o["bbox"] = [x1, y1, x2, y2]
            out.append(o)
    return out


def nms_by_iob(objects, thresh=0.8):
    objects = sorted(objects, key=lambda o: o["score"], reverse=True)
    keep = []

    for obj in objects:
        discard = False
        for kept in keep:
            if iob(obj["bbox"], kept["bbox"]) >= thresh:
                discard = True
                break
        if not discard:
            keep.append(obj)

    return keep


# Row / Column postprocess
def refine_rows_columns(rows, columns):
    rows = nms_by_iob(rows, 0.8)
    columns = nms_by_iob(columns, 0.8)

    rows.sort(key=lambda r: (r["bbox"][1] + r["bbox"][3]) / 2)
    columns.sort(key=lambda c: (c["bbox"][0] + c["bbox"][2]) / 2)

    if not rows or not columns:
        return rows, columns

    table_xmin = min(c["bbox"][0] for c in columns)
    table_xmax = max(c["bbox"][2] for c in columns)
    table_ymin = min(r["bbox"][1] for r in rows)
    table_ymax = max(r["bbox"][3] for r in rows)

    for r in rows:
        r["bbox"][0] = table_xmin
        r["bbox"][2] = table_xmax

    for c in columns:
        c["bbox"][1] = table_ymin
        c["bbox"][3] = table_ymax

    return rows, columns


# Spanning cell postprocess=
def overlap_y(a, b):
    inter = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    h = min(a[3] - a[1], b[3] - b[1])
    return inter / h if h > 0 else 0


def overlap_x(a, b):
    inter = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    w = min(a[2] - a[0], b[2] - b[0])
    return inter / w if w > 0 else 0


def refine_spanning_cells(spans, rows, columns):
    refined = []

    for s in spans:
        row_nums = [i for i, r in enumerate(rows) if overlap_y(s["bbox"], r["bbox"]) >= 0.5]
        col_nums = [j for j, c in enumerate(columns) if overlap_x(s["bbox"], c["bbox"]) >= 0.5]

        if not row_nums or not col_nums:
            continue

        x1 = min(columns[j]["bbox"][0] for j in col_nums)
        y1 = min(rows[i]["bbox"][1] for i in row_nums)
        x2 = max(columns[j]["bbox"][2] for j in col_nums)
        y2 = max(rows[i]["bbox"][3] for i in row_nums)

        s["row_nums"] = row_nums
        s["column_nums"] = col_nums
        s["bbox"] = [x1, y1, x2, y2]

        refined.append(s)

    refined.sort(key=lambda s: s["score"], reverse=True)

    final = []
    for s in refined:
        conflict = False
        for k in final:
            if set(s["row_nums"]) & set(k["row_nums"]) and \
                    set(s["column_nums"]) & set(k["column_nums"]):
                conflict = True
                break
        if not conflict:
            final.append(s)

    return final


# Main processing
model = None


def get_model():
    global model
    if model is None:
        print(">>> Loading TableExtractionPipeline ...")
        model = TableExtractionPipeline(
            det_device="cpu",
            str_device="cpu",
            det_model_path=None,
            str_model_path="./model/model_3.pth"
        )
    return model


def table_structure_recognize(image_path: str, xml_output_folder: str):
    os.makedirs(xml_output_folder, exist_ok=True)

    img_cv = cv2.imread(image_path)
    h, w, d = img_cv.shape

    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)

    model = get_model()
    result = model.recognize(img_pil, out_objects=True)

    objects = filter_small_boxes(result["objects"], min_size=5)

    rows = [o for o in objects if o["label"] == "table row"]
    columns = [o for o in objects if o["label"] == "table column"]
    spans = [o for o in objects if o["label"] == "table spanning cell"]

    rows, columns = refine_rows_columns(rows, columns)
    spans = refine_spanning_cells(spans, rows, columns)

    final_objects = []

    for o in rows + columns + spans:
        if o["score"] < 0.8:
            continue

        final_objects.append({
            "label": o["label"],
            "bbox": tuple(map(int, o["bbox"]))
        })

    filename = os.path.basename(image_path)
    xml_path = os.path.join(
        xml_output_folder,
        os.path.splitext(filename)[0] + ".xml"
    )

    boxes_to_voc_xml(
        final_objects,
        xml_path,
        image_size=(w, h, d),
        image_filename=filename
    )
