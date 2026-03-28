"""
Writer — sprema Document na disk.

Podržani formati:
  .pyword  — prošireni plain text (naš nativni format)
  .txt     — čisti plain text bez ikakvih prefiksa
"""

import os
from .doc import Document


def save(doc: Document, path: str = None) -> str:
    """
    Sprema dokument. Vraća putanju na kojoj je snimljeno.
    Ako path nije naveden, koristi doc.filepath.
    Raises OSError ako ne može pisati.
    """
    target = path or doc.filepath
    if not target:
        raise ValueError("Nije navedena putanja za snimanje.")

    ext = os.path.splitext(target)[1].lower()

    if ext == ".txt":
        content = _to_plain_text(doc)
    else:
        # .pyword ili bez ekstenzije → naš format
        if not ext:
            target += ".pyword"
        content = _to_pyword(doc)

    with open(target, "w", encoding="utf-8") as f:
        f.write(content)

    doc.filepath = target
    doc.mark_clean()
    return target


def _to_pyword(doc: Document) -> str:
    """Prošireni plain text — paragrafi odvojeni praznim retkom."""
    return "\n\n".join(doc.get_texts())


def _to_plain_text(doc: Document) -> str:
    """
    Čisti plain text:
      - naslovi (#, ##, ###) → samo tekst bez prefiksa
      - liste ("  - ") → "- " bez uvlake
      - tablice (tab-odvojeni) → ostaju kao jesu
      - paragrafi odvojeni praznim retkom
    """
    lines = []
    for text in doc.get_texts():
        if text.startswith("### "):
            lines.append(text[4:])
        elif text.startswith("## "):
            lines.append(text[3:])
        elif text.startswith("# "):
            lines.append(text[2:])
        elif text.startswith("  - "):
            lines.append("- " + text[4:])
        else:
            lines.append(text)
    return "\n\n".join(lines)


def load_pyword(path: str) -> Document:
    """Učitava .pyword datoteku."""
    from .doc import Document
    doc = Document()
    doc.filepath = path

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # paragrafi odvojeni praznim retkom
    raw_paragraphs = content.split("\n\n")
    # unutar paragrafa može biti više redaka — spajamo ih u jedan Edit
    texts = []
    for block in raw_paragraphs:
        texts.append(block.rstrip("\n"))

    doc.set_paragraphs(texts if texts else [""])
    return doc


def load_txt(path: str) -> Document:
    """Učitava .txt — svaki dvostruki newline = novi paragraf."""
    from .doc import Document
    doc = Document()
    doc.filepath = path

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    raw = content.split("\n\n")
    texts = [block.rstrip("\n") for block in raw]
    doc.set_paragraphs(texts if texts else [""])
    return doc
