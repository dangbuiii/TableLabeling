import xml.etree.ElementTree as ET


def voc_xml_to_boxes(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    boxes = []
    for obj in root.findall("object"):
        name = obj.findtext("name")
        bb = obj.find("bndbox")

        xmin = int(bb.findtext("xmin"))
        ymin = int(bb.findtext("ymin"))
        xmax = int(bb.findtext("xmax"))
        ymax = int(bb.findtext("ymax"))

        boxes.append({
            "label": name,
            "bbox": (xmin, ymin, xmax, ymax)
        })

    return boxes


def boxes_to_voc_xml(objects, filename, image_size, image_filename=""):
    w, h, d = image_size

    root = ET.Element("annotation")
    ET.SubElement(root, "filename").text = image_filename

    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(w)
    ET.SubElement(size, "height").text = str(h)
    ET.SubElement(size, "depth").text = str(d)

    for obj in objects:
        o = ET.SubElement(root, "object")
        ET.SubElement(o, "name").text = obj["label"]

        b = ET.SubElement(o, "bndbox")
        x1, y1, x2, y2 = map(int, obj["bbox"])

        ET.SubElement(b, "xmin").text = str(x1)
        ET.SubElement(b, "ymin").text = str(y1)
        ET.SubElement(b, "xmax").text = str(x2)
        ET.SubElement(b, "ymax").text = str(y2)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(filename, encoding="utf-8")
