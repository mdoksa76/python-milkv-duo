"""
Document model za pyword.
Struktura: Document sadrži listu Paragraph objekata.
Format u memoriji i na disku je prošireni plain text:
  - paragrafi odvojeni praznim retkom
  - naslovi: # ## ###
  - liste:   - item (uvlaka tabom)
  - tablice: stupci s \t, redovi s \n
"""


class Paragraph:
    __slots__ = ("text",)

    def __init__(self, text=""):
        self.text = text

    def is_heading(self):
        return self.text.startswith("#")

    def heading_level(self):
        count = 0
        for ch in self.text:
            if ch == "#":
                count += 1
            else:
                break
        return min(count, 3)

    def heading_text(self):
        return self.text.lstrip("#").lstrip()

    def __repr__(self):
        preview = self.text[:40].replace("\n", " ")
        return f"Paragraph({preview!r})"


class Document:
    def __init__(self):
        self.paragraphs: list[Paragraph] = []
        self.filepath: str | None = None
        self.dirty: bool = False

    def is_empty(self):
        return not self.paragraphs or all(p.text == "" for p in self.paragraphs)

    def set_paragraphs(self, texts: list[str]):
        self.paragraphs = [Paragraph(t) for t in texts]
        self.dirty = False

    def get_texts(self) -> list[str]:
        return [p.text for p in self.paragraphs]

    def mark_dirty(self):
        self.dirty = True

    def mark_clean(self):
        self.dirty = False

    @classmethod
    def new(cls):
        doc = cls()
        doc.paragraphs = [Paragraph("")]
        return doc
