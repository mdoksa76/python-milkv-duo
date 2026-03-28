"""
ODF reader — koristi odfpy, lazy import.
odfpy se učitava tek pri prvom pozivu load(), ne pri startu aplikacije.

Podržava .odt (Writer dokumenti).
Izvlači:
  - paragrafe (text:p)
  - naslovi (text:h level=1/2/3 → # ## ###)
  - liste (text:list-item → "  - ")
  - tablice (table:table → tab-odvojeni stupci)
"""

from .doc import Document


def _heading_prefix(level):
    return {1: "#", 2: "##", 3: "###"}.get(level, "###")


def _extract_text(elem):
    """Rekurzivno izvlači tekst iz ODF elementa."""
    parts = []
    if elem.firstChild is None:
        return ""
    child = elem.firstChild
    while child is not None:
        from odf.element import Text as OdfText
        import odf.text as odft
        if hasattr(child, "data"):
            parts.append(child.data)
        elif hasattr(child, "tagName"):
            tag = child.tagName
            if tag == "text:tab":
                parts.append("\t")
            elif tag == "text:line-break":
                parts.append(" ")
            else:
                parts.append(_extract_text(child))
        child = child.nextSibling
    return "".join(parts)


def _parse_table(table_elem):
    """ODF tablica → lista stringova (tab-odvojeni stupci)."""
    import odf.table as odftbl
    rows = []
    for row in table_elem.getElementsByType(odftbl.TableRow):
        cells = []
        for cell in row.getElementsByType(odftbl.TableCell):
            import odf.text as odft
            cell_parts = []
            for p in cell.getElementsByType(odft.P):
                cell_parts.append(_extract_text(p).strip())
            cells.append(" ".join(cell_parts))
        rows.append("\t".join(cells))
    return rows


def load(path: str) -> Document:
    # lazy import — odfpy se ne učitava dok nije potreban
    try:
        from odf.opendocument import load as odf_load
        import odf.text as odft
        import odf.table as odftbl
    except ImportError:
        doc = Document()
        doc.filepath = path
        doc.set_paragraphs(["[Greška: odfpy nije instaliran. pip install odfpy]"])
        return doc

    doc = Document()
    doc.filepath = path
    paragraphs = []

    odf_doc = odf_load(path)
    body = odf_doc.text

    def process_element(elem):
        tag = getattr(elem, "tagName", "")

        if tag == "text:h":
            try:
                from odf.namespaces import TEXTNS
                level = int(elem.attributes.get((TEXTNS, "outline-level"), 1))
            except Exception:
                level = 1
            text = _extract_text(elem).strip()
            if text:
                paragraphs.append(f"{_heading_prefix(level)} {text}")

        elif tag == "text:p":
            text = _extract_text(elem).strip()
            paragraphs.append(text)

        elif tag == "text:list":
            for item in elem.getElementsByType(odft.ListItem):
                for p in item.getElementsByType(odft.P):
                    text = _extract_text(p).strip()
                    if text:
                        paragraphs.append(f"  - {text}")

        elif tag == "table:table":
            rows = _parse_table(elem)
            paragraphs.extend(rows)

        else:
            # rekurzivno kroz ostale elemente (text:section itd.)
            child = getattr(elem, "firstChild", None)
            while child is not None:
                process_element(child)
                child = getattr(child, "nextSibling", None)

    child = body.firstChild
    while child is not None:
        process_element(child)
        child = child.nextSibling

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
