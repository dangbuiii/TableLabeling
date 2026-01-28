import numpy as np
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

def get_bbox(image: np.ndarray):

    result = ocr.predict(input=image)
    if not result:
        return []

    res = result[0]
    texts = res["rec_texts"]
    polys = res["rec_polys"]

    def poly_to_bbox(poly):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return min(xs), min(ys), max(xs), max(ys)

    def merge_bbox(b1, b2):
        return (
            min(b1[0], b2[0]),
            min(b1[1], b2[1]),
            max(b1[2], b2[2]),
            max(b1[3], b2[3]),
        )

    def first_alpha_char(text):
        for c in text:
            if c.isalpha():
                return c
        return None

    merged_bboxes = []
    merged_texts = []

    for text, poly in zip(texts, polys):
        bbox = poly_to_bbox(poly)
        first_char = first_alpha_char(text)

        if (
            merged_bboxes
            and first_char is not None
            and first_char.islower()
        ):
            merged_bboxes[-1] = merge_bbox(merged_bboxes[-1], bbox)
            merged_texts[-1] += " " + text
        else:
            merged_bboxes.append(bbox)
            merged_texts.append(text)

    return merged_bboxes
