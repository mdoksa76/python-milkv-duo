#!/usr/bin/env python3

import sys
import requests
from lxml import html
from urllib.parse import urljoin, quote_plus

def fetch_page(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def parse_page(url, html_text):
    tree = html.fromstring(html_text)

    # Ukloni sve elemente koje ne želimo
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

    # Tekstualni sadržaj
    texts = tree.xpath("//text()")
    cleaned = [t.strip() for t in texts if t.strip()]
    text_output = "\n".join(cleaned)

    # Linkovi
    links = []
    for a in tree.xpath("//a[@href]"):
        href = a.get("href")
        label = (a.text or "").strip()
        full_url = urljoin(url, href)
        if full_url.startswith("http"):
            links.append((label or full_url, full_url))

    return text_output, links

def main():
    if len(sys.argv) < 2:
        print("Upotreba: python pylinx.py <URL>")
        sys.exit(1)

    history = []
    current_url = sys.argv[1]

    while True:
        try:
            html_text = fetch_page(current_url)
        except Exception as e:
            print(f"Greška pri dohvaćanju: {e}")
            if history:
                current_url = history.pop()
                continue
            else:
                break

        text, links = parse_page(current_url, html_text)

        print("\n" + "="*80)
        print(f"URL: {current_url}")
        print("="*80 + "\n")
        print(text)
        print("\n" + "-"*80)
        print("Linkovi:")
        for i, (label, url) in enumerate(links, 1):
            print(f"[{i}] {label} -> {url}")
        print("-"*80)
        print("Opcije: broj = otvori link, b = nazad, u = novi URL, s = Brave search, q = izlaz")

        choice = input("Odaberi: ").strip()

        if choice == "q":
            break

        if choice == "b":
            if history:
                current_url = history.pop()
            else:
                print("Nema nazad.")
            continue

        if choice == "u":
            new_url = input("Unesi novi URL: ").strip()
            if not new_url.startswith("http"):
                print("URL mora početi s http ili https.")
                continue
            history.append(current_url)
            current_url = new_url
            continue

        # 🟩 Brave Search prečac
        if choice.startswith("s "):
            query = choice[2:].strip()
            encoded = quote_plus(query)
            brave_url = f"https://search.brave.com/search?q={encoded}&source=web&summary=0"
            history.append(current_url)
            current_url = brave_url
            continue

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(links):
                history.append(current_url)
                current_url = links[idx][1]
            else:
                print("Nevažeći broj.")
        else:
            print("Nepoznata opcija.")

if __name__ == "__main__":
    main()
