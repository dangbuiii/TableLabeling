from bs4 import BeautifulSoup
import re

def html_to_token_structure(html):
    with open(html, "r", encoding="utf-8") as file:
        html_content = file.read()
    soup = BeautifulSoup(html_content, "html.parser")
    tokens = []

    def process_tag(tag):
        if isinstance(tag, str):
            return  # skip raw text inside <td>TEMP</td>

        name = tag.name.lower()
        if name in {"table", "thead", "tbody", "tr", "td"}:
            if name in {"table", "thead", "tbody", "tr"}:
                tokens.append(f"<{name}>")
                for child in tag.children:
                    process_tag(child)
                tokens.append(f"</{name}>")
            elif name == "td":
                has_attributes = False  # Kiểm tra nếu thẻ có thuộc tính colspan hoặc rowspan
                attr_tokens = [f"<td"]
                for attr, val in tag.attrs.items():
                    if attr in {"colspan", "rowspan"}:
                        has_attributes = True
                        attr_tokens.append(f' {attr}="{val}"')
                if has_attributes:
                    attr_tokens.append(">")
                
                if not has_attributes:
                    tokens.append("<td>")
                    tokens.append("</td>")
                else:
                    tokens.extend(attr_tokens)
                    tokens.append("</td>")

    # Process top-level tags
    for child in soup.contents:
        process_tag(child)

    return {"tokens": tokens}


# Example usage:
# html = '<table><thead><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td colspan=\"2\">TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr></thead><tbody><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td colspan=\"2\">TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr><tr><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td><td>TEMP</td></tr></tbody></table>'

# result = html_to_token_structure("D:\\working\\KSE\\OCR_Tax_Tables\\datasets\\data_HoaDonTaiChinhVN\\Dang\\phase_1\\BC_TaiChinh\\62_table0.html")

# print(result)

