#!/usr/bin/env python3

import sys
import os
import requests
from lxml import html
from urllib.parse import urljoin, quote_plus
import tempfile
import json
import shutil
import textwrap
import re
import chardet

import urwid

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

BOOKMARK_FILE = "bookmarks.json"

# Fokusirani panel: 0=content, 1=links, 2=images
PANEL_CONTENT = 0
PANEL_LINKS   = 1
PANEL_IMAGES  = 2

# ---------------- STATE ---------------- #

class LinkEntry:
    def __init__(self, label, url):
        self.label = label
        self.url = url
        self.selected = False

class ImageEntry:
    def __init__(self, url):
        self.url = url
        self.selected = False

class PageState:
    def __init__(self):
        self.url = ""
        self.title = ""
        self.content_paragraphs = []
        self.links = []
        self.images = []
        self.bookmarks = []

state = PageState()

# ---------------- BOOKMARKS ---------------- #

def load_bookmarks():
    if not os.path.exists(BOOKMARK_FILE):
        return []
    try:
        with open(BOOKMARK_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    bookmarks = []
    for item in data:
        if isinstance(item, str):
            bookmarks.append({"title": item, "url": item})
        elif isinstance(item, dict) and "url" in item:
            title = item.get("title") or item["url"]
            bookmarks.append({"title": title, "url": item["url"]})
    return bookmarks

def save_bookmarks(bookmarks):
    try:
        with open(BOOKMARK_FILE, "w") as f:
            json.dump(bookmarks, f, indent=2)
    except IOError as e:
        pass  # nema gdje logirati u TUI kontekstu

# ---------------- FETCHING ---------------- #

def fetch_page(url):
    """Dohvati stranicu i automatski detektiraj encoding"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout: {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Nema konekcije: {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP {e.response.status_code}: {url}")

    content = r.content
    detected = chardet.detect(content)
    detected_encoding = detected['encoding'] if detected['encoding'] else 'utf-8'

    try:
        return content.decode(detected_encoding)
    except (UnicodeDecodeError, LookupError):
        for enc in ['utf-8', 'windows-1250', 'iso-8859-2', 'cp1250']:
            try:
                return content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return content.decode('utf-8', errors='ignore')

def download_image(url):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        r.raise_for_status()
        fd, path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return path
    except (requests.exceptions.RequestException, IOError):
        return None

# ---------------- PARSING ---------------- #

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_page(url, html_text):
    tree = html.fromstring(html_text)

    title_nodes = tree.xpath("//title/text()")
    title = title_nodes[0].strip() if title_nodes else url

    images = []
    for img in tree.xpath("//img[@src]"):
        src = img.get("src")
        full = urljoin(url, src)
        if full.startswith("http"):
            images.append(full)

    remove_tags = [
        "script", "style", "noscript", "header", "footer", "nav", "aside",
        "form", "svg", "canvas", "video", "audio", "iframe", "img",
        "input", "button", "select", "option", "link", "meta"
    ]
    for tag in remove_tags:
        for elem in tree.xpath(f"//{tag}"):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)

    texts = tree.xpath("//text()")
    cleaned = [t.strip() for t in texts if t.strip()]

    paragraphs = []
    current = ""
    for line in cleaned:
        current += " " + line
        if len(line) >= 60 or line.endswith((".", "!", "?", ":", ";")):
            paragraphs.append(current.strip())
            current = ""
    if current.strip():
        paragraphs.append(current.strip())

    paragraphs = [clean_text(p) for p in paragraphs if p.strip()]
    text_output = "\n\n".join(paragraphs)

    links = []
    seen_urls = set()
    for a in tree.xpath("//a[@href]"):
        href = a.get("href")
        label = a.text_content().strip()
        full_url = urljoin(url, href)

        if not full_url.startswith("http") or full_url in seen_urls:
            continue

        label = clean_text(label) if label else full_url
        if len(label) > 60:
            label = label[:60] + "..."

        seen_urls.add(full_url)
        links.append((label, full_url))

    return text_output, links, images, title

# ---------------- SELECTABLE TEXT (za linkove bez Button) ---------------- #

class SelectableText(urwid.Text):
    """Tekst koji prima fokus i reagira na Enter/space."""
    _selectable = True

    def keypress(self, size, key):
        return key  # proslijedi gore, handle_keys će uhvatiti

# ---------------- MAIN TUI ---------------- #

class PyLinksTUI:
    def __init__(self, start_url):
        self.history = []
        self.current_url = start_url
        self.current_title = start_url
        self.active_panel = PANEL_CONTENT  # koji panel je fokusiran
        self.main_loop = None
        state.bookmarks = load_bookmarks()

        # --- Gornji info bar ---
        self.url_text  = urwid.Text(f"🌐 {self.current_url}")
        self.title_text = urwid.Text("📄 Loading...")

        # --- CONTENT panel ---
        self.content_walker = urwid.SimpleFocusListWalker([urwid.Text("")])
        self.content_list   = urwid.ListBox(self.content_walker)
        self.content_box    = urwid.LineBox(
            urwid.AttrMap(self.content_list, 'content'),
            title="CONTENT"
        )

        # --- LINKS panel ---
        self.links_walker = urwid.SimpleFocusListWalker([urwid.Text("")])
        self.links_list   = urwid.ListBox(self.links_walker)
        self.links_box    = urwid.LineBox(
            urwid.AttrMap(self.links_list, 'links'),
            title="LINKS"
        )

        # --- IMAGES panel ---
        self.images_walker = urwid.SimpleFocusListWalker([urwid.Text("")])
        self.images_list   = urwid.ListBox(self.images_walker)
        self.images_box    = urwid.LineBox(
            urwid.AttrMap(self.images_list, 'images'),
            title="IMAGES"
        )

        # --- Donji red (links + images) ---
        self.bottom_columns = urwid.Columns([
            ('weight', 6, self.links_box),
            ('weight', 5, self.images_box),
        ])

        # --- Bottom toolbar (tipke) ---
        self.bottom_toolbar = urwid.Columns([
            ('pack', urwid.Button('🖼️ Image [i]',    self.on_view_image)),
            ('pack', urwid.Button('🔖 Bookmark [b]', self.on_bookmark_menu)),
            ('pack', urwid.Button('⬅️ Back [BkSp]',  self.on_back)),
            ('pack', urwid.Button('🔄 Refresh [r]',  self.on_refresh)),
            ('pack', urwid.Button('🌐 URL [u]',       self.on_new_url)),
            ('pack', urwid.Button('🔍 Search [s]',    self.on_brave_search)),
            ('pack', urwid.Button('🚪 Exit [q]',      self.on_exit)),
        ])

        # --- Status bar ---
        self.status_text = urwid.Text(
            "F1=Content  F2=Links  F3=Images  Tab=Next panel  Enter=Open  q=Quit"
        )

        # --- Glavni layout — jednom kreiran, nikad rebuild ---
        self.main_pile = urwid.Pile([
            ('pack', self.url_text),
            ('pack', self.title_text),
            ('weight', 2, self.content_box),
            ('weight', 1, self.bottom_columns),
            ('pack', self.bottom_toolbar),
            ('pack', self.status_text),
        ])

        self.frame = urwid.Frame(self.main_pile)

        # Palette
        self.palette = [
            ('content',        'light gray',    'black'),
            ('links',          'light cyan',    'black'),
            ('images',         'light magenta', 'black'),
            ('selected',       'white',         'dark blue'),
            ('focused_panel',  'white',         'dark blue'),
            ('button',         'white',         'dark gray'),
            ('bookmark',       'yellow',        'dark blue'),
            ('error',          'light red',     'black'),
            ('status',         'black',         'dark cyan'),
        ]

        # Učitaj prvu stranicu
        self.load_page(self.current_url)

    # ------------------------------------------------------------------ #
    #  FOKUS PANELA
    # ------------------------------------------------------------------ #

    def _set_active_panel(self, panel_id):
        self.active_panel = panel_id
        panel_map = {
            PANEL_CONTENT: "F1=Content ◀  F2=Links  F3=Images  Tab=Next  Enter=Open  q=Quit",
            PANEL_LINKS:   "F1=Content  F2=Links ◀  F3=Images  Tab=Next  Enter=Open link  q=Quit",
            PANEL_IMAGES:  "F1=Content  F2=Links  F3=Images ◀  Tab=Next  Enter=View image  q=Quit",
        }
        self.status_text.set_text(panel_map.get(panel_id, ""))
        if self.main_loop:
            self.main_loop.draw_screen()

    def _focus_panel(self, panel_id):
        """Postavi urwid fokus na odabrani ListBox."""
        self._set_active_panel(panel_id)
        try:
            if panel_id == PANEL_CONTENT:
                self.main_pile.focus_item = self.content_box
                self.content_list._emit('postchange')
            elif panel_id == PANEL_LINKS:
                self.main_pile.focus_item = self.bottom_columns
                self.bottom_columns.focus_position = 0
            elif panel_id == PANEL_IMAGES:
                self.main_pile.focus_item = self.bottom_columns
                self.bottom_columns.focus_position = 1
        except Exception:
            pass
        if self.main_loop:
            self.main_loop.draw_screen()

    # ------------------------------------------------------------------ #
    #  GRADNJA REDOVA
    # ------------------------------------------------------------------ #

    def _build_link_row(self, link_entry):
        label = link_entry.label
        if len(label) > 52:
            label = label[:52] + "…"
        btn = urwid.Button(label)
        urwid.connect_signal(btn, 'click', self._on_link_open, link_entry)
        return urwid.AttrMap(btn, None, focus_map='selected')

    def _build_image_row(self, image_entry):
        filename = image_entry.url.split('/')[-1][:35]
        btn = urwid.Button(f"🖼️ {filename}")
        urwid.connect_signal(btn, 'click', self._on_image_view, image_entry)
        return urwid.AttrMap(btn, None, focus_map='selected')

    def _build_content_paragraphs(self, text):
        self.content_walker[:] = []
        term_width = shutil.get_terminal_size((80, 24)).columns
        width = max(40, term_width - 6)
        for para in text.split("\n\n"):
            if para.strip():
                wrapped = textwrap.fill(para, width=width)
                self.content_walker.append(urwid.Text(wrapped))
                self.content_walker.append(urwid.Text(""))
        if not self.content_walker:
            self.content_walker.append(urwid.Text("(No content)"))

    # ------------------------------------------------------------------ #
    #  SIGNAL HANDLERI ZA KLIK
    # ------------------------------------------------------------------ #

    def _on_link_open(self, button, link_entry):
        self.history.append(self.current_url)
        self.current_url = link_entry.url
        self.load_page(self.current_url)

    def _on_image_view(self, button, image_entry):
        self.view_image(image_entry.url)

    # ------------------------------------------------------------------ #
    #  LOAD PAGE — ne rekreira widget tree
    # ------------------------------------------------------------------ #

    def load_page(self, url):
        self.status_text.set_text(f"Loading: {url}")
        if self.main_loop:
            self.main_loop.draw_screen()

        try:
            html_text = fetch_page(url)
            text, links, images, title = parse_page(url, html_text)
        except RuntimeError as e:
            self.status_text.set_text(f"❌ {e}")
            if self.main_loop:
                self.main_loop.draw_screen()
            return
        except Exception as e:
            self.status_text.set_text(f"Unexpected error: {e}")
            if self.main_loop:
                self.main_loop.draw_screen()
            return

        self.current_title = title
        self.current_url   = url

        # Ažuriraj state
        state.url    = url
        state.title  = title
        state.links  = [LinkEntry(lbl, u) for lbl, u in links]
        state.images = [ImageEntry(img_url) for img_url in images]

        # Ažuriraj info bar
        self.url_text.set_text(f"🌐 {url}")
        self.title_text.set_text(f"📄 {title}")

        # Ažuriraj content walker (in-place)
        self._build_content_paragraphs(text)

        # Ažuriraj links walker (in-place)
        self.links_walker[:] = [
            self._build_link_row(link) for link in state.links[:50]
        ]
        if not self.links_walker:
            self.links_walker.append(urwid.Text("(No links)"))

        # Ažuriraj images walker (in-place)
        self.images_walker[:] = [
            self._build_image_row(img) for img in state.images[:20]
        ]
        if not self.images_walker:
            self.images_walker.append(urwid.Text("(No images)"))

        # Ažuriraj naslove panela — samo text unutar LineBox title
        # LineBox nema setter, ali možemo ga zamijeniti in-place u Pile
        # Najlakše: status bar nosi info
        self.status_text.set_text(
            f"✅ {len(state.links)} links, {len(state.images)} images |  "
            f"F1=Content  F2=Links  F3=Images  Tab=Next  q=Quit"
        )

        if self.main_loop:
            self.main_loop.draw_screen()

    # ------------------------------------------------------------------ #
    #  IMAGE VIEWER
    # ------------------------------------------------------------------ #

    def view_image(self, url):
        self.status_text.set_text("Load image...")
        if self.main_loop:
            self.main_loop.draw_screen()

        proxy = "https://images.weserv.nl/?output=png&url=" + url
        path  = download_image(proxy)

        if path:
            if self.main_loop:
                self.main_loop.stop()
            os.system('clear')
            os.system(f'python3 imgview.py "{path}"')
            try:
                os.unlink(path)  # očisti temp fajl
            except OSError:
                pass
            if self.main_loop:
                self.main_loop.start()
                self.main_loop.screen.clear()
                self.main_loop.draw_screen()
            self.status_text.set_text("✅ Image viewed")
        else:
            self.status_text.set_text("❌ Image unloadable")
            if self.main_loop:
                self.main_loop.draw_screen()

    # ------------------------------------------------------------------ #
    #  BOOKMARK POPUP
    # ------------------------------------------------------------------ #

    def show_bookmark_popup(self):
        sorted_bookmarks = sorted(state.bookmarks, key=lambda b: b["title"].lower())

        items = []
        for i, bm in enumerate(sorted_bookmarks, 1):
            items.append(urwid.Text(f"[{i}] {bm['title']}"))
            items.append(urwid.Text(f"    {bm['url']}"))
            items.append(urwid.Divider())

        if not items:
            items = [urwid.Text("No bookmarks", align='center')]

        listbox = urwid.ListBox(urwid.SimpleListWalker(items))
        listbox = urwid.BoxAdapter(listbox, height=min(15, max(3, len(items))))

        self.bookmark_edit = urwid.Edit("Broj: ", "")
        self.popup_status  = urwid.Text("", align='center')

        buttons = urwid.Columns([
            urwid.Button('+ Dodaj', self.on_popup_add),
            urwid.Button('↗ Open', self.on_popup_open),
            urwid.Button('✕ Delete', self.on_popup_delete),
            urwid.Button('✖ Close', self.on_popup_close),
        ])

        pile = urwid.Pile([
            urwid.Text("── BOOKMARKS ──", align='center'),
            urwid.Divider(),
            listbox,
            urwid.Divider(),
            self.bookmark_edit,
            urwid.Divider(),
            buttons,
            self.popup_status,
        ])

        overlay = urwid.Overlay(
            urwid.LineBox(pile),
            self.main_pile,
            'center', ('relative', 70),
            'middle', ('relative', 75),
        )
        self.frame.body = overlay
        if self.main_loop:
            self.main_loop.draw_screen()

    def on_popup_add(self, button):
        if not any(bm["url"] == self.current_url for bm in state.bookmarks):
            state.bookmarks.append({"title": self.current_title, "url": self.current_url})
            save_bookmarks(state.bookmarks)
            self.popup_status.set_text(("bookmark", "✅ Added"))
        else:
            self.popup_status.set_text(("error", "❌ Already exist"))
        self.show_bookmark_popup()

    def _get_bookmark_idx(self):
        """Vrati indeks iz bookmark edit polja ili None."""
        try:
            idx = int(self.bookmark_edit.edit_text.strip()) - 1
            sorted_bm = sorted(state.bookmarks, key=lambda b: b["title"].lower())
            if 0 <= idx < len(sorted_bm):
                return idx, sorted_bm
        except ValueError:
            pass
        return None, []

    def on_popup_open(self, button):
        idx, sorted_bm = self._get_bookmark_idx()
        if idx is not None:
            self.history.append(self.current_url)
            self.current_url = sorted_bm[idx]["url"]
            self.restore_main_view()
            self.load_page(self.current_url)
        else:
            self.popup_status.set_text(("error", "❌ Unregular number"))
            if self.main_loop:
                self.main_loop.draw_screen()

    def on_popup_delete(self, button):
        idx, sorted_bm = self._get_bookmark_idx()
        if idx is not None:
            to_remove = sorted_bm[idx]
            state.bookmarks[:] = [b for b in state.bookmarks if b["url"] != to_remove["url"]]
            save_bookmarks(state.bookmarks)
            self.popup_status.set_text(("bookmark", f"✅ Deleted: {to_remove['title']}"))
            self.show_bookmark_popup()
        else:
            self.popup_status.set_text(("error", "❌ Unregular number"))
            if self.main_loop:
                self.main_loop.draw_screen()

    def on_popup_close(self, button):
        self.restore_main_view()

    def restore_main_view(self):
        self.frame.body = self.main_pile
        if self.main_loop:
            self.main_loop.draw_screen()

    # ------------------------------------------------------------------ #
    #  BUTTON HANDLERI
    # ------------------------------------------------------------------ #

    def on_refresh(self, button=None):
        self.load_page(self.current_url)

    def on_back(self, button=None):
        if self.history:
            self.current_url = self.history.pop()
            self.load_page(self.current_url)
        else:
            self.status_text.set_text("No previous page")
            if self.main_loop:
                self.main_loop.draw_screen()

    def on_new_url(self, button=None):
        if self.main_loop:
            self.main_loop.stop()
        os.system('clear')
        new_url = input("Input URL: ").strip()
        if new_url:
            if not new_url.startswith("http"):
                new_url = "https://" + new_url
            self.history.append(self.current_url)
            self.current_url = new_url
        if self.main_loop:
            self.main_loop.start()
            self.main_loop.screen.clear()
            self.load_page(self.current_url)

    def on_brave_search(self, button=None):
        if self.main_loop:
            self.main_loop.stop()
        os.system('clear')
        query = input("Brave search: ").strip()
        if query:
            encoded  = quote_plus(query)
            brave_url = f"https://search.brave.com/search?q={encoded}&source=web"
            self.history.append(self.current_url)
            self.current_url = brave_url
        if self.main_loop:
            self.main_loop.start()
            self.main_loop.screen.clear()
            self.load_page(self.current_url)

    def on_bookmark_menu(self, button=None):
        self.show_bookmark_popup()

    def on_view_image(self, button=None):
        # Otvori trenutno fokusiranu sliku u images panelu
        if state.images:
            try:
                focus_pos = self.images_list.focus_position
                if 0 <= focus_pos < len(state.images):
                    self.view_image(state.images[focus_pos].url)
                    return
            except IndexError:
                pass
        self.status_text.set_text("No image")
        if self.main_loop:
            self.main_loop.draw_screen()

    def on_exit(self, button=None):
        raise urwid.ExitMainLoop()

    # ------------------------------------------------------------------ #
    #  KEYBOARD NAVIGATION
    # ------------------------------------------------------------------ #

    def handle_keys(self, key):
        # Izlaz
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

        # F-keys — direktni skok na panel
        if key == 'f1':
            self._focus_panel(PANEL_CONTENT)
            return
        if key == 'f2':
            self._focus_panel(PANEL_LINKS)
            return
        if key == 'f3':
            self._focus_panel(PANEL_IMAGES)
            return

        # Tab — ciklički skok između panela
        if key == 'tab':
            next_panel = (self.active_panel + 1) % 3
            self._focus_panel(next_panel)
            return

        # Shift+Tab — obrnuto
        if key == 'shift tab':
            next_panel = (self.active_panel - 1) % 3
            self._focus_panel(next_panel)
            return

        # Enter — otvori fokusirani link ili sliku
        if key == 'enter':
            if self.active_panel == PANEL_LINKS:
                try:
                    pos = self.links_list.focus_position
                    if 0 <= pos < len(state.links):
                        self.history.append(self.current_url)
                        self.current_url = state.links[pos].url
                        self.load_page(self.current_url)
                except (IndexError, AttributeError):
                    pass
            elif self.active_panel == PANEL_IMAGES:
                try:
                    pos = self.images_list.focus_position
                    if 0 <= pos < len(state.images):
                        self.view_image(state.images[pos].url)
                except (IndexError, AttributeError):
                    pass
            return

        # Backspace — back
        if key == 'backspace':
            self.on_back()
            return

        # Prečaci za akcije (van popup-a)
        if isinstance(self.frame.body, urwid.Pile):  # nismo u popupu
            if key in ('r', 'R'):
                self.on_refresh()
                return
            if key in ('u', 'U'):
                self.on_new_url()
                return
            if key in ('s', 'S'):
                self.on_brave_search()
                return
            if key in ('b', 'B'):
                self.on_bookmark_menu()
                return
            if key in ('i', 'I'):
                self.on_view_image()
                return

        # Escape — zatvori popup ako je otvoren
        if key == 'esc':
            if not isinstance(self.frame.body, urwid.Pile):
                self.restore_main_view()
            return

    # ------------------------------------------------------------------ #
    #  RUN
    # ------------------------------------------------------------------ #

    def run(self):
        self.main_loop = urwid.MainLoop(
            self.frame,
            self.palette,
            unhandled_input=self.handle_keys
        )
        self.main_loop.run()


def main():
    if len(sys.argv) < 2:
        print("Usage: pylinks-tui.py <URL>")
        sys.exit(1)
    app = PyLinksTUI(sys.argv[1])
    app.run()

if __name__ == "__main__":
    main()
