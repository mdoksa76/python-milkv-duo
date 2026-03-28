"""
DOCX reader — koristi samo stdlib: zipfile + xml.etree.ElementTree
Nema ovisnosti o python-docx.

Izvlači:
  - paragrafe (w:p)
  - naslovi (w:pStyle Heading1/2/3 → # ## ###)
  - tablice (w:tbl → tab-odvojeni stupci)
  - liste (w:numPr → prefiks "  - ")
"""

import zipfile
import xml.etree.ElementTree as ET
from .doc import Document

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _tag(name):
    return f"{{{_W}}}{name}"


def _runs_text(p_elem):
    """Spaja tekst svih w:r run-ova unutar paragrafa."""
    parts = []
    for r in p_elem.iter(_tag("r")):
        for t in r.iter(_tag("t")):
            parts.append(t.text or "")
    return "".join(parts)


def _heading_prefix(p_elem):
    """Vraća '#', '##' ili '###' ako je paragraf naslov, inače ''."""
    pPr = p_elem.find(_tag("pPr"))
    if pPr is None:
        return ""
    pStyle = pPr.find(_tag("pStyle"))
    if pStyle is None:
        return ""
    val = pStyle.get(_tag("val"), "")
    mapping = {
        "Heading1": "#", "Heading2": "##", "Heading3": "###",
        "heading1": "#", "heading2": "##", "heading3": "###",
        "1": "#", "2": "##", "3": "###",
    }
    return mapping.get(val, "")


def _is_list_item(p_elem):
    pPr = p_elem.find(_tag("pPr"))
    if pPr is None:
        return False
    return pPr.find(_tag("numPr")) is not None


def _parse_table(tbl_elem):
    """Tablica → lista stringova (jedan string po retku, stupci s \\t)."""
    rows = []
    for tr in tbl_elem.iter(_tag("tr")):
        cells = []
        for tc in tr.iter(_tag("tc")):
            cell_text_parts = []
            for p in tc.iter(_tag("p")):
                cell_text_parts.append(_runs_text(p))
            cells.append(" ".join(cell_text_parts).strip())
        rows.append("\t".join(cells))
    return rows


def load(path: str) -> Document:
    doc = Document()
    doc.filepath = path
    paragraphs = []

    with zipfile.ZipFile(path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)

    root = tree.getroot()
    body = root.find(f".//{_tag('body')}")
    if body is None:
        doc.set_paragraphs([""])
        return doc

    for child in body:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if local == "p":
            text = _runs_text(child).strip()
            prefix = _heading_prefix(child)
            if prefix:
                if text:
                    paragraphs.append(f"{prefix} {text}")
            elif _is_list_item(child):
                if text:
                    paragraphs.append(f"  - {text}")
            else:
                paragraphs.append(text)

        elif local == "tbl":
            rows = _parse_table(child)
            paragraphs.extend(rows)

    # ukloni višestruke uzastopne prazne retke
    cleaned = []
    prev_empty = False
    for p in paragraphs:
        is_empty = p.strip() == ""
        if is_empty and prev_empty:
            continue
        cleaned.append(p)
        prev_empty = is_empty

    doc.set_paragraphs(cleaned if cleaned else [""])
    return doc
