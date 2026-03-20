# pylinks — Terminal Web Browser with Image Support  
A minimalistic terminal-based web browser designed for extremely low‑power devices such as the Milkv Duo SBC.  
Displays text, links, and images (via an external image proxy), with support for thumbnail and fullscreen rendering.

---

# 🇬🇧 English Version

## 🚀 Features

### ✔ Clean terminal web browsing
- HTML parsing with lxml  
- Automatic removal of unnecessary elements (script, style, nav, ads, etc.)  
- Clean, readable text output  
- Simple and intuitive navigation  

### ✔ Navigation
- Select links by number  
- Go back to previous page  
- Enter a new URL  
- Built‑in Brave Search (`s query`)  

### ✔ Image display in terminal
- Thumbnail mode (`img N`)  
- Fullscreen mode (`i N`)  
- Automatic scaling based on terminal size  
- Image info header (original size + rendered size)  
- Uses `plotext` for ASCII‑style rendering  

### ✔ External image proxy (no local JPEG decoder required)
The Milkv Duo SBC has:
- no libjpeg  
- no ffmpeg  
- no package manager  
- very limited RAM (~55 MB available)  

Therefore, pylinks uses **images.weserv.nl**, which:
- Accepts any image format (JPG, PNG, WEBP, AVIF, HEIC, SVG…)  
- Converts it to PNG on the server  
- Sends a PNG that Pillow can decode  
- Offloads all heavy processing away from the device  

This makes image viewing possible even on extremely weak hardware.

### ✔ Ultra‑low resource usage
- Tested on **Milkv Duo SBC (~55 MB RAM available)**  
- No X11, Wayland, or framebuffer required  
- Runs in a pure terminal environment  

---

## 📦 Required Software

Install these Python packages:

pip install requests lxml pillow plotext


No additional system packages are required.

Not needed:
- libjpeg  
- ffmpeg  
- opkg/apk/apt  
- X11 or framebuffer  

---

## 🧩 Project Structure

pylinks.py   → main terminal web browser
imgview.py   → image viewer using plotext
README.md    → documentation


---

## 🖼 How image rendering works

1. pylinks extracts `<img src="...">` URLs  
2. Instead of downloading the image directly, it uses:

https://images.weserv.nl/?output=png&url= (images.weserv.nl in Bing)<original-url>


3. The proxy converts the image to PNG  
4. PNG is downloaded locally  
5. `imgview.py` displays it using plotext  

This allows image viewing without any local decoders.

---

## 🕹 Controls

| Command | Action |
|--------|--------|
| `number` | Open link |
| `img N` | Thumbnail image |
| `i N` | Fullscreen image |
| `b` | Back |
| `u` | New URL |
| `s query` | Brave Search |
| `q` | Quit |

---

## 🛠 Running

pylinks.py https://example.com


---

## 📌 Why this project is special

- Works on devices without JPEG support  
- Requires no external tools  
- Displays real images in terminal  
- Lightweight, fast, and stable  
- Better than ASCIIview and similar tools  
- Unique architecture: **cloud‑based image decoding**  
- Ideal for embedded Linux, IoT, and ultra‑low‑power systems  

---

## 📜 License
Free to use, modify, and share.

---

# 🇭🇷 Hrvatska Verzija

## 🚀 Značajke

### ✔ Čisto pregledavanje weba u terminalu
- Parsiranje HTML‑a pomoću lxml  
- Automatsko uklanjanje nepotrebnih elemenata (script, style, nav…)  
- Jasan i čitljiv tekstualni prikaz  
- Jednostavna navigacija  

### ✔ Navigacija
- Odabir linkova brojem  
- Povratak na prethodnu stranicu  
- Unos novog URL‑a  
- Brave Search (`s pojam`)  

### ✔ Prikaz slika u terminalu
- Thumbnail prikaz (`img N`)  
- Fullscreen prikaz (`i N`)  
- Automatsko skaliranje prema veličini terminala  
- Informacije o slici (originalne dimenzije + prikazane dimenzije)  
- plotext ASCII prikaz  

### ✔ Vanjski image proxy (bez lokalnog JPEG dekodera)
Milkv Duo SBC nema:
- libjpeg  
- ffmpeg  
- package manager  
- puno RAM‑a (oko 55 MB dostupno)  

Zato pylinks koristi **images.weserv.nl**, koji:
- prima bilo koji format (JPG, PNG, WEBP, AVIF, HEIC, SVG…)  
- pretvara ga u PNG na serveru  
- šalje PNG koji Pillow može otvoriti  
- rasterizira sliku na serveru, ne na uređaju  

Ovo omogućuje prikaz slika čak i na vrlo slabom hardveru.

### ✔ Minimalni resursi
- Testirano na **Milkv Duo SBC (~55 MB RAM dostupno)**  
- Ne treba X11, Wayland ni framebuffer  
- Radi u čistom terminalu  

---

## 📦 Potreban softver

Instaliraj Python pakete:

pip install requests lxml pillow plotext


Nije potrebno:
- libjpeg  
- ffmpeg  
- opkg/apk/apt  
- X11  

---

## 🧩 Struktura projekta

pylinks.py   → glavni web preglednik
imgview.py   → prikaz slika u terminalu
README.md    → dokumentacija


---

## 🖼 Kako radi prikaz slika

1. pylinks pronađe `<img src="...">`  
2. Umjesto direktnog skidanja slike, koristi:

https://images.weserv.nl/?output=png&url= (images.weserv.nl in Bing)<original-url>


3. Proxy konvertira sliku u PNG  
4. PNG se skida lokalno  
5. `imgview.py` prikazuje sliku preko plotext‑a  

Ovo omogućuje prikaz slika bez ikakvih lokalnih dekodera.

---

## 🕹 Kontrole

| Komanda | Funkcija |
|--------|----------|
| `broj` | Otvori link |
| `img N` | Thumbnail prikaz |
| `i N` | Fullscreen prikaz |
| `b` | Nazad |
| `u` | Novi URL |
| `s pojam` | Brave Search |
| `q` | Izlaz |

---

## 🛠 Pokretanje

pylinks.py https://example.com


---

## 📌 Zašto je ovaj projekt poseban

- Radi na uređajima bez JPEG podrške  
- Ne treba nikakve dodatne alate  
- Prikazuje stvarne slike u terminalu  
- Lagano, brzo i stabilno  
- Bolje od ASCIIview i sličnih alata  
- Jedinstvena arhitektura: **cloud dekodiranje slika**  
- Idealno za embedded Linux i IoT uređaje  

---

## 📜 Licenca
Slobodno koristi, mijenjaj i dijeli.
