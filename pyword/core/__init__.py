from .doc import Document, Paragraph
from .docx_reader import load as load_docx
from .odf_reader import load as load_odf
from .writer import save, load_pyword, load_txt
import os

PLAIN_TEXT_EXTS = {
    ".txt", ".md", ".py", ".sh", ".json",
    ".xml", ".html", ".ini", ".cfg", ".log",
}

ODF_EXTS = {".odt", ".ods", ".odp"}

SUPPORTED_EXTS = {".docx", ".pyword"} | ODF_EXTS | PLAIN_TEXT_EXTS


def open_file(path: str) -> Document:
    """Otvara datoteku prema ekstenziji."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return load_docx(path)
    elif ext in ODF_EXTS:
        return load_odf(path)
    elif ext == ".pyword":
        return load_pyword(path)
    else:
        # sve ostale ekstenzije + nepoznate → plain text
        return load_txt(path)
