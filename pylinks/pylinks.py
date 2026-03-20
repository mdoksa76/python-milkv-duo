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

from colorama import Fore, Style, init
init(autoreset=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

BOOKMARK_FILE = "bookmarks.json"

# ---------------- BOOKMARKS ---------------- #

def load_bookmarks():
    if not os.path.exists(BOOKMARK_FILE):
        return []
    try:
        with open(BOOKMARK_FILE, "r") as f:
            data = json.load(f)
    except:
        return []

    bookmarks = []
    for item in data:
        if isinstance(item, str):
            bookmarks.append({"title": item, "url": item})
        elif isinstance(item, dict) and "url" in item:
            title = item.get("title") or item["url"]
            bookmarks.append({"title": title, "url": item["url"]})

    bookmarks.sort(key=lambda b: b["title"].lower())
    return bookmarks

def save_bookmarks(bookmarks):
    bookmarks_sorted = sorted(bookmarks, key=lambda b: b["title"].lower())
    with open(BOOKMARK_FILE, "w") as f:
        json.dump(bookmarks_sorted, f, indent=2)

def show_bookmarks(bookmarks):
    print(Fore.MAGENTA + "\nBookmarks:")
    if not bookmarks:
        print("  (nema spremljenih bookmarkova)")
        return
    for i, bm in enumerate(sorted(bookmarks, key=lambda b: b["title"].lower()), 1):
        print(Fore.CYAN + f"[{i}] {bm['title']}")
        print("    " + bm["url"])

def bookmark_menu(current_url, current_title, bookmarks, history):
    while True:
        print(Fore.MAGENTA + "\n=== BOOKMARK MENU ===")
        print("a = add current page")
        print("v = view bookmarks")
        print("o N = open bookmark number N")
        print("d N = delete bookmark number N")
        print("q = quit bookmark menu")

        cmd = input("Bookmark command: ").strip()

        if cmd == "q":
            return current_url

        if cmd == "a":
            if not any(bm["url"] == current_url for bm in bookmarks):
                title = current_title or current_url
                bookmarks.append({"title": title, "url": current_url})
                save_bookmarks(bookmarks)
                print(Fore.GREEN + "Dodano u bookmarke.")
            else:
                print(Fore.RED + "Već postoji u bookmarkovima.")
            continue

        if cmd == "v":
            show_bookmarks(bookmarks)
            continue

        if cmd.startswith("o "):
            try:
                idx = int(cmd[2:]) - 1
                sorted_bm = sorted(bookmarks, key=lambda b: b["title"].lower())
                if 0 <= idx < len(sorted_bm):
                    history.append(current_url)
                    return sorted_bm[idx]["url"]
                else:
                    print(Fore.RED + "Nevažeći broj bookmarka.")
            except:
                print(Fore.RED + "Krivi format.")
            continue

        if cmd.startswith("d "):
            try:
                idx = int(cmd[2:]) - 1
                bookmarks_sorted = sorted(bookmarks, key=lambda b: b["title"].lower())
                if 0 <= idx < len(bookmarks_sorted):
                    to_remove = bookmarks_sorted[idx]
                    bookmarks[:] = [bm for bm in bookmarks if bm["url"] != to_remove["url"]]
                    save_bookmarks(bookmarks)
                    print(Fore.RED + f"Obrisano: {to_remove['title']}")
                else:
                    print(Fore.RED + "Nevažeći broj bookmarka.")
            except:
                print(Fore.RED + "Krivi format.")
            continue

        print(Fore.RED + "Nepoznata bookmark komanda.")

# ---------------- FETCHING ---------------- #

def fetch_page(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def download_image(url):
    try:
        r = requests.get(url, headers=HEADERS, stream=True)
        r.raise_for_status()

        fd, path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        return path
    except:
        return None

# ---------------- PARSING ---------------- #

def clean_text(text):
    # Ukloni višestruke razmake i nove redove
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

    # Ukloni nepotrebne elemente (isto kao u inicijalnom kodu)
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

    # Prikupi sav tekst (isto kao u inicijalnom kodu)
    texts = tree.xpath("//text()")
    cleaned = [t.strip() for t in texts if t.strip()]

    # Spoji u paragrafe (poboljšana verzija)
    paragraphs = []
    current = ""
    
    for line in cleaned:
        # Ako je linija kratka i ne završava rečenicu → nastavak
        if (len(line) < 60 and not line.endswith((".", "!", "?", ":", ";"))):
            current += " " + line
        else:
            current += " " + line
            paragraphs.append(current.strip())
            current = ""

    if current.strip():
        paragraphs.append(current.strip())

    # Očisti svaki paragraf
    paragraphs = [clean_text(p) for p in paragraphs if p.strip()]
    
    text_output = "\n\n".join(paragraphs)

    # Prikupi linkove
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

# ---------------- RENDERING ---------------- #

def print_header(url, title):
    width = shutil.get_terminal_size().columns
    line = "═" * (width - 2)
    print(Fore.GREEN + f"╔{line}╗")
    print(Fore.GREEN + f"║ URL: {url}")
    print(Fore.YELLOW + f"║ TITLE: {title}")
    print(Fore.GREEN + f"╚{line}╝")

def print_status_bar():
    width = shutil.get_terminal_size().columns
    print(Fore.MAGENTA + "─" * width)
    print(Fore.MAGENTA + "Commands: number=open link, img N=thumbnail, i N=fullscreen, b=back, u=new URL, s query=Brave search, l=bookmarks, q=quit")

# ---------------- MAIN LOOP ---------------- #

def main():
    if len(sys.argv) < 2:
        print("Usage: python pylinks.py <URL>")
        sys.exit(1)

    history = []
    current_url = sys.argv[1]
    current_title = current_url
    bookmarks = load_bookmarks()

    while True:
        os.system("clear")

        try:
            html_text = fetch_page(current_url)
        except Exception as e:
            print(Fore.RED + f"Error fetching page: {e}")
            if history:
                current_url = history.pop()
                continue
            else:
                break

        text, links, images, current_title = parse_page(current_url, html_text)

        # --- SECTION 1: TEXT ONLY ---
        print_header(current_url, current_title)
        
        # Prikaz teksta
        width = shutil.get_terminal_size().columns - 4
        wrapper = textwrap.TextWrapper(width=width, replace_whitespace=False)
        
        if text:
            for paragraph in text.split("\n\n"):
                if paragraph.strip():
                    # Zamotaj paragraf
                    wrapped = wrapper.fill(paragraph)
                    print("\n" + wrapped)
        else:
            print(Fore.RED + "\nNo text content found.")
        
        print("\n")

        input(Fore.MAGENTA + "Press ENTER to show links and images...")

        # --- SECTION 2: LINKS + IMAGES ---
        os.system("clear")
        print_header(current_url, current_title)
        
        print(Fore.MAGENTA + "\n" + "="*60)
        print(Fore.MAGENTA + "LINKS")
        print(Fore.MAGENTA + "="*60)
        
        if links:
            for i, (label, url) in enumerate(links, 1):
                print(Fore.CYAN + f"[{i}] {label}")
                print(Fore.YELLOW + f"    {url}")
                print()
        else:
            print(Fore.RED + "No links found.\n")

        print(Fore.MAGENTA + "="*60)
        print(Fore.MAGENTA + "IMAGES")
        print(Fore.MAGENTA + "="*60)
        
        if images:
            for i, url in enumerate(images, 1):
                print(Fore.CYAN + f"[IMG{i}] {url}")
        else:
            print(Fore.RED + "No images found.")

        print()
        print_status_bar()

        # --- COMMANDS ---
        choice = input("Command: ").strip()

        if choice == "q":
            break

        if choice == "b":
            if history:
                current_url = history.pop()
            else:
                print(Fore.RED + "No previous page.")
            continue

        if choice == "u":
            new_url = input("Enter new URL: ").strip()
            if not new_url.startswith("http"):
                print(Fore.RED + "URL must start with http or https.")
                continue
            history.append(current_url)
            current_url = new_url
            continue

        if choice.startswith("s "):
            query = quote_plus(choice[2:].strip())
            brave = f"https://search.brave.com/search?q={query}&source=web"
            history.append(current_url)
            current_url = brave
            continue

        if choice == "l":
            current_url = bookmark_menu(current_url, current_title, bookmarks, history)
            continue

        if choice.startswith("img "):
            try:
                idx = int(choice[4:]) - 1
            except:
                print(Fore.RED + "Invalid image index.")
                continue

            if 0 <= idx < len(images):
                proxy = "https://images.weserv.nl/?output=png&url=" + images[idx]
                path = download_image(proxy)
                if path:
                    os.system(f"python3 imgview.py --thumb '{path}'")
            else:
                print(Fore.RED + "Image index out of range.")
            continue

        if choice.startswith("i "):
            try:
                idx = int(choice[2:]) - 1
            except:
                print(Fore.RED + "Invalid image index.")
                continue

            if 0 <= idx < len(images):
                proxy = "https://images.weserv.nl/?output=png&url=" + images[idx]
                path = download_image(proxy)
                if path:
                    os.system(f"python3 imgview.py '{path}'")
            else:
                print(Fore.RED + "Image index out of range.")
            continue

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(links):
                history.append(current_url)
                current_url = links[idx][1]
            else:
                print(Fore.RED + "Invalid link number.")
            continue

        print(Fore.RED + "Unknown command.")

if __name__ == "__main__":
    main()
