#!/usr/bin/env python3
"""
pymail.py - TUI mail klient (Thunderbird layout)
Python 3.9.5+, pure Python dependencies only
Requires: urwid (pip install urwid)

Layout:
  [FolderPane | MessageListPane ]
  [           | MessagePane     ]
"""

import urwid
import imaplib
import email
import email.header
import email.utils
import html.parser
import os
import json
import socket
import threading
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG  (edit or load from ~/.pymailrc)
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    "accounts": [
        {
            "name": "Gmail",
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "imap_ssl": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "smtp_ssl": True,
            "smtp_starttls": False,
            "username": "your.email@gmail.com",
            "password": "",
            "_note": "password = 16-znak Google App Password bez razmaka",
            "sent_folder": "[Gmail]/Sent Mail",
            "folder_exclude": ["Sent", "Drafts", "INBOX/Trash"]
        }
    ]
}

CONFIG_PATH = os.path.expanduser("~/.pymailrc")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    # Write default config and return it
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG


# ─────────────────────────────────────────────
# HTML STRIPPER
# ─────────────────────────────────────────────

class HTMLStripper(html.parser.HTMLParser):
    SKIP_TAGS = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        if tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def get_text(self):
        text = "".join(self.parts)
        # Collapse multiple blank lines
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def strip_html(html_text):
    s = HTMLStripper()
    try:
        s.feed(html_text)
        return s.get_text()
    except Exception:
        return html_text


def decode_header_str(raw):
    """Decode RFC2047 encoded header into plain string."""
    parts = email.header.decode_header(raw or "")
    result = []
    for byt, enc in parts:
        if isinstance(byt, bytes):
            try:
                result.append(byt.decode(enc or "utf-8", errors="replace"))
            except Exception:
                result.append(byt.decode("latin-1", errors="replace"))
        else:
            result.append(byt)
    return "".join(result)


def get_body(msg):
    """Extract best text body from email.message.Message."""
    body = ""
    if msg.is_multipart():
        # Prefer text/plain, fallback to text/html
        plain = None
        html_part = None
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            if ct == "text/plain" and plain is None:
                plain = part
            elif ct == "text/html" and html_part is None:
                html_part = part
        chosen = plain or html_part
        if chosen:
            charset = chosen.get_content_charset() or "utf-8"
            payload = chosen.get_payload(decode=True)
            if payload:
                body = payload.decode(charset, errors="replace")
                if chosen.get_content_type() == "text/html":
                    body = strip_html(body)
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                body = strip_html(body)
    return body or "(No content)"



# ─────────────────────────────────────────────
# ATTACHMENT HANDLER
# ─────────────────────────────────────────────

ATTACH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attachments")


def ensure_attach_dir():
    os.makedirs(ATTACH_DIR, exist_ok=True)
    return ATTACH_DIR


def list_attachments(msg):
    """
    Return list of dicts for each attachment part:
    { name, content_type, size, part }
    """
    found = []
    if not msg:
        return found
    for part in msg.walk():
        cd = str(part.get("Content-Disposition", ""))
        ct = part.get_content_type()
        filename = part.get_filename()
        if not filename and "attachment" not in cd:
            continue
        if not filename:
            ext = ct.split("/")[-1] if "/" in ct else "bin"
            filename = f"attachment.{ext}"
        filename = decode_header_str(filename)
        payload = part.get_payload(decode=True) or b""
        found.append({
            "name": filename,
            "content_type": ct,
            "size": len(payload),
            "part": part,
        })
    return found


def save_attachment(attach_info):
    """Save attachment to ATTACH_DIR. Returns saved path."""
    ensure_attach_dir()
    payload = attach_info["part"].get_payload(decode=True) or b""
    # Sanitize filename
    safe = "".join(c if c.isalnum() or c in "._- " else "_"
                   for c in attach_info["name"]).strip()
    if not safe:
        safe = "attachment.bin"
    dest = os.path.join(ATTACH_DIR, safe)
    # Avoid overwrite
    if os.path.exists(dest):
        base, ext = os.path.splitext(safe)
        i = 1
        while os.path.exists(dest):
            dest = os.path.join(ATTACH_DIR, f"{base}_{i}{ext}")
            i += 1
    with open(dest, "wb") as f:
        f.write(payload)
    return dest


def pdf_to_text(payload_bytes):
    """
    Extract text from PDF bytes using pypdf (pure Python).
    Falls back to raw byte hint if pypdf not available.
    """
    try:
        import io
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(payload_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i+1} ---\n{text.strip()}")
        return "\n\n".join(pages) if pages else "(No extractable text in PDF)"
    except ImportError:
        return "(pypdf not installed — run: pip3 install pypdf)"
    except Exception as e:
        return f"(PDF read error: {e})"




def odt_to_text(payload_bytes):
    """
    Extract text from ODT/ODS/ODP bytes using odfpy (pure Python).
    pip3 install odfpy
    """
    try:
        import io, re
        from odf.opendocument import load as odf_load

        doc = odf_load(io.BytesIO(payload_bytes))
        lines = []

        def collect(node):
            """Recursively collect text, append newline after each paragraph/heading."""
            buf = []
            for child in node.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    buf.append(child.data)
                else:
                    # Check local name (second element of qname tuple)
                    local = child.qname[1] if hasattr(child, "qname") else ""
                    if local in ("p", "h"):
                        # Recurse into paragraph/heading, then emit as a line
                        inner = []
                        _collect_text(child, inner)
                        lines.append("".join(inner))
                    elif local == "line-break":
                        buf.append("\n")
                    elif local == "tab":
                        buf.append("\t")
                    else:
                        collect(child)
            if buf:
                lines.append("".join(buf))

        def _collect_text(node, out):
            for child in node.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    out.append(child.data)
                else:
                    local = child.qname[1] if hasattr(child, "qname") else ""
                    if local == "line-break":
                        out.append("\n")
                    elif local == "tab":
                        out.append("\t")
                    else:
                        _collect_text(child, out)

        collect(doc.text)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text or "(No extractable text in ODT)"
    except ImportError:
        return "(odfpy not installed — run: pip3 install odfpy)"
    except Exception as e:
        return f"(ODT read error: {e})"


def docx_to_text(payload_bytes):
    """
    Extract text from DOCX bytes using mammoth (pure Python).
    pip3 install mammoth
    Paragraphs separated by newlines.
    """
    try:
        import io, re
        import mammoth

        # convert_to_markdown preserves paragraph breaks better than extract_raw_text
        result = mammoth.convert_to_markdown(io.BytesIO(payload_bytes))
        text = result.value

        # Clean up markdown syntax — remove # headings markers, * bold/italic
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
        text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
        # Normalise excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text or "(No extractable text in DOCX)"
    except ImportError:
        return "(mammoth not installed — run: pip3 install mammoth)"
    except Exception as e:
        return f"(DOCX read error: {e})"


def doc_type(name, ct):
    """Return 'pdf', 'odt', 'docx', or None."""
    n = name.lower()
    if ct == "application/pdf" or n.endswith(".pdf"):
        return "pdf"
    if ct in ("application/vnd.oasis.opendocument.text",
              "application/vnd.oasis.opendocument.spreadsheet",
              "application/vnd.oasis.opendocument.presentation") or \
       n.endswith((".odt", ".ods", ".odp")):
        return "odt"
    if ct in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              "application/msword") or \
       n.endswith((".docx", ".doc")):
        return "docx"
    return None


def decode_imap_utf7(s):
    """
    Decode IMAP modified UTF-7 encoded folder names.
    e.g. "&AWE-" -> "š", "&AX4-" -> "ć"
    Spec: RFC 3501 section 5.1.3
    """
    # If no & present, nothing to decode
    if "&" not in s:
        return s
    import base64
    result = []
    i = 0
    while i < len(s):
        if s[i] == "&":
            j = s.find("-", i + 1)
            if j == -1:
                result.append(s[i:])
                break
            encoded = s[i+1:j]
            if encoded == "":
                # "&-" is literal "&"
                result.append("&")
            else:
                # Modified base64: replace "," with "/" then decode as UTF-16BE
                try:
                    b64 = encoded.replace(",", "/")
                    # Pad to multiple of 4
                    pad = (4 - len(b64) % 4) % 4
                    decoded = base64.b64decode(b64 + "=" * pad)
                    result.append(decoded.decode("utf-16-be"))
                except Exception:
                    result.append(s[i:j+1])
            i = j + 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


# ─────────────────────────────────────────────
# IMAP CLIENT
# ─────────────────────────────────────────────

class IMAPClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self.conn = None

    def connect(self):
        if self.cfg.get("imap_ssl", True):
            self.conn = imaplib.IMAP4_SSL(
                self.cfg["imap_host"], self.cfg.get("imap_port", 993)
            )
        else:
            self.conn = imaplib.IMAP4(
                self.cfg["imap_host"], self.cfg.get("imap_port", 143)
            )
        self.conn.login(self.cfg["username"], self.cfg["password"])
        self.folder_map = {}

    def disconnect(self):
        if self.conn:
            try:
                self.conn.logout()
            except Exception:
                pass
            self.conn = None

    def list_folders(self):
        """
        Return list of decoded folder name strings for display.
        Also populates self.folder_map = {decoded_name: raw_imap_name}
        so we can send the correct UTF-7 name back to the server.
        """
        folders = []
        self.folder_map = {}
        try:
            typ, data = self.conn.list()
            if typ != "OK":
                return folders
            for item in data:
                if isinstance(item, bytes):
                    item = item.decode("utf-8", errors="replace")
                # Parse: (\HasNoChildren) "/" "INBOX"  or  ... / FolderName
                parts = item.split('"')
                if len(parts) >= 3:
                    raw = parts[-2].strip()
                elif " " in item:
                    raw = item.rsplit(" ", 1)[-1].strip().strip('"')
                else:
                    raw = item.strip()
                raw = raw.strip()
                if raw:
                    decoded = decode_imap_utf7(raw)
                    self.folder_map[decoded] = raw
                    folders.append(decoded)
        except Exception as e:
            folders.append(f"[Error: {e}]")
        return folders

    def imap_name(self, display_name):
        """Convert display folder name back to raw IMAP UTF-7 name."""
        return getattr(self, "folder_map", {}).get(display_name, display_name)

    def select_folder(self, folder):
        """Select folder, return message count."""
        try:
            raw = self.imap_name(folder)
            typ, data = self.conn.select(f'"{raw}"')
            if typ == "OK":
                return int(data[0])
        except Exception:
            pass
        return 0

    def fetch_list(self, folder, page=1, per_page=50):
        """
        Fetch message summaries for the folder.
        Returns list of dicts: uid, subject, from, date, seen
        Newest first.
        """
        messages = []
        try:
            count = self.select_folder(folder)
            if count == 0:
                return messages

            # Calculate range (newest first)
            end = count - (page - 1) * per_page
            start = max(1, end - per_page + 1)
            if end < 1:
                return messages

            seq = f"{start}:{end}"
            typ, data = self.conn.fetch(seq, "(FLAGS ENVELOPE)")
            if typ != "OK" or not data:
                return messages

            for item in reversed(data):
                if not isinstance(item, tuple):
                    continue
                raw = item[1].decode("utf-8", errors="replace") if isinstance(item[1], bytes) else str(item[1])
                # Parse FLAGS
                seen = "\\Seen" in item[0].decode("utf-8", errors="replace") if isinstance(item[0], bytes) else False
                # Use email.message for envelope parsing via full fetch
                # We'll do a lightweight parse here
                uid = None
                uid_match = item[0]
                if isinstance(uid_match, bytes):
                    parts = uid_match.decode().split()
                    if parts:
                        try:
                            uid = int(parts[0])
                        except ValueError:
                            uid = parts[0]

                # Parse ENVELOPE from raw
                subj = self._parse_envelope_field(raw, "subject") or "(no subject)"
                frm  = self._parse_envelope_field(raw, "from")    or ""
                date = self._parse_envelope_field(raw, "date")    or ""

                messages.append({
                    "uid": uid,
                    "subject": decode_header_str(subj),
                    "from": frm,
                    "date": self._format_date(date),
                    "seen": seen,
                })
        except Exception as e:
            messages.append({"uid": None, "subject": f"[Error: {e}]", "from": "", "date": "", "seen": True})
        return messages

    def _parse_envelope_field(self, raw, field):
        """Very simple ENVELOPE field extractor."""
        # Fall back to nothing - we'll use RFC822 fetch for reliability
        return ""

    def _format_date(self, date_str):
        if not date_str:
            return ""
        try:
            dt = email.utils.parsedate_to_datetime(date_str)
            now = datetime.now()
            if dt.date() == now.date():
                return dt.strftime("%H:%M")
            elif dt.year == now.year:
                return dt.strftime("%d.%m")
            else:
                return dt.strftime("%d.%m.%y")
        except Exception:
            return date_str[:10] if len(date_str) > 10 else date_str

    def fetch_headers(self, folder, page=1, per_page=50):
        """
        Reliable header fetch using RFC822.HEADER.
        Returns list of dicts. Newest first.
        page=1 fetches newest per_page messages, page=2 fetches next older, etc.
        """
        messages = []
        try:
            count = self.select_folder(folder)
            if count == 0:
                return messages

            # newest-first: page 1 = [count .. count-per_page+1]
            end = count - (page - 1) * per_page
            start = max(1, end - per_page + 1)
            if end < 1:
                return messages
            # Clamp end to valid range
            end = min(end, count)

            seq = f"{start}:{end}"
            # Fetch FLAGS + HEADER
            typ, flag_data = self.conn.fetch(seq, "(FLAGS)")
            typ2, hdr_data = self.conn.fetch(seq, "(RFC822.HEADER)")

            flags_map = {}
            if typ == "OK":
                for item in flag_data:
                    if isinstance(item, tuple):
                        raw = item[0].decode("utf-8", errors="replace") if isinstance(item[0], bytes) else str(item[0])
                        parts = raw.split()
                        if parts:
                            try:
                                num = int(parts[0])
                                flags_map[num] = "\\Seen" in raw
                            except Exception:
                                pass

            if typ2 == "OK":
                items = [x for x in hdr_data if isinstance(x, tuple)]
                for item in reversed(items):
                    raw_num = item[0].decode("utf-8", errors="replace") if isinstance(item[0], bytes) else str(item[0])
                    num_str = raw_num.split()[0]
                    try:
                        num = int(num_str)
                    except ValueError:
                        num = None
                    seen = flags_map.get(num, False)

                    hdr_bytes = item[1] if isinstance(item[1], bytes) else item[1].encode()
                    msg = email.message_from_bytes(hdr_bytes)

                    subj = decode_header_str(msg.get("Subject", "(no subject)"))
                    frm  = decode_header_str(msg.get("From", ""))
                    date = msg.get("Date", "")

                    messages.append({
                        "uid": num,
                        "subject": subj,
                        "from": frm,
                        "date": self._format_date(date),
                        "seen": seen,
                    })

        except Exception as e:
            messages.append({
                "uid": None,
                "subject": f"[Fetch error: {e}]",
                "from": "", "date": "", "seen": True
            })
        return messages

    def fetch_message(self, uid):
        """Fetch full message by sequence number. Returns email.Message."""
        try:
            typ, data = self.conn.fetch(str(uid), "(RFC822)")
            if typ == "OK" and data and isinstance(data[0], tuple):
                raw = data[0][1]
                return email.message_from_bytes(raw)
        except Exception as e:
            return None
        return None

    def mark_seen(self, uid):
        try:
            self.conn.store(str(uid), "+FLAGS", "\\Seen")
        except Exception:
            pass


# ─────────────────────────────────────────────
# SMTP CLIENT
# ─────────────────────────────────────────────

class SMTPClient:
    """
    Gmail SMTP via STARTTLS (port 587).
    Koristi stdlib smtplib — nula extra dependencija.
    Auth: Gmail App Password (16 znakova).
    """

    def __init__(self, cfg):
        self.cfg = cfg

    def send(self, to_addr, subject, body, reply_to=None, attachments=None):
        """
        Send plain-text mail, optionally with attachments.
        to_addr     : str (comma-separated) or list of str
        subject     : str
        body        : str (plain text)
        reply_to    : original email.Message for Reply (In-Reply-To header)
        attachments : list of (filename, content_type, bytes) tuples
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders

        # Parse comma-separated recipients
        if isinstance(to_addr, str):
            to_addr = [a.strip() for a in to_addr.split(",") if a.strip()]

        # Use mixed for attachments, alternative for plain text only
        if attachments:
            msg = MIMEMultipart("mixed")
            msg.attach(MIMEText(body, "plain", "utf-8"))
        else:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain", "utf-8"))

        msg["From"]    = self.cfg["username"]
        msg["To"]      = ", ".join(to_addr)
        msg["Subject"] = subject

        # Reply/Forward threading headers
        if reply_to is not None:
            mid = reply_to.get("Message-ID", "")
            if mid:
                msg["In-Reply-To"] = mid
                msg["References"]  = mid

        # Attach files: list of (filename, content_type, bytes)
        for fname, ctype, data in (attachments or []):
            maintype, subtype = ctype.split("/", 1) if "/" in ctype else ("application", "octet-stream")
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=fname)
            msg.attach(part)

        host    = self.cfg.get("smtp_host", "smtp.gmail.com")
        port    = self.cfg.get("smtp_port", 587)
        use_tls = self.cfg.get("smtp_starttls", True)
        use_ssl = self.cfg.get("smtp_ssl", False)

        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as s:
                s.ehlo()
                s.login(self.cfg["username"], self.cfg["password"])
                s.sendmail(self.cfg["username"], to_addr, msg.as_bytes())
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.ehlo()
                if use_tls:
                    s.starttls()
                    s.ehlo()
                s.login(self.cfg["username"], self.cfg["password"])
                s.sendmail(self.cfg["username"], to_addr, msg.as_bytes())


# ─────────────────────────────────────────────
# COMPOSE DIALOG
# ─────────────────────────────────────────────

class ComposeDialog(urwid.WidgetWrap):
    """
    Modalni compose prozor.
    Keys: Tab = next field, F2 = send, Esc = cancel
    """

    signals = ["send", "cancel"]

    def __init__(self, to="", subject="", body="", title="New message"):
        self.fields = {}
        self.user_attachments = []  # list of (filename, content_type, bytes)
        self._picker_overlay = None

        def edit(label, content="", multiline=False):
            ed = urwid.Edit(("compose_label", f"{label}: "), content, multiline=multiline)
            return urwid.AttrMap(ed, "compose_field", "compose_field_focus"), ed

        to_box,   self.f_to      = edit("To     ", to)
        subj_box, self.f_subject = edit("Subject", subject)

        self.f_body = urwid.Edit("", body, multiline=True)
        body_box = urwid.AttrMap(self.f_body, "compose_field", "compose_field_focus")

        self.attach_text = urwid.Text(("body_text", ""), wrap="clip")

        hint = urwid.Text(
            [("key_hint", " F2"), ("status", ":send  "),
             ("key_hint", "F3"), ("status", ":attach  "),
             ("key_hint", "Esc"), ("status", ":cancel  "),
             ("key_hint", "Tab"), ("status", ":next field")],
        )

        self._pile = urwid.Pile([
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            to_box,
            subj_box,
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            urwid.BoxAdapter(urwid.ListBox(urwid.SimpleListWalker([body_box])), height=10),
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            self.attach_text,
            urwid.AttrMap(hint, "status"),
        ])

        self._box = urwid.LineBox(self._pile, title=title, title_align="left")
        self._w = self._box

    def _refresh_attach_line(self):
        if self.user_attachments:
            names = "  ".join(f"[{a[0]}]" for a in self.user_attachments)
            self.attach_text.set_text(("body_header", f" Attachments: {names}"))
        else:
            self.attach_text.set_text(("body_text", ""))

    def _open_picker(self):
        """Open inline file picker overlay."""
        picker = _FilePicker(start_dir=os.path.expanduser("~"))

        def on_pick():
            path = getattr(picker, "selected_path", None)
            self._w = self._box  # restore compose
            if path and os.path.isfile(path):
                self._add_attachment(path)

        def on_cancel():
            self._w = self._box

        urwid.connect_signal(picker, "pick",   on_pick)
        urwid.connect_signal(picker, "cancel", on_cancel)

        self._w = urwid.Overlay(
            picker, self._box,
            align="center", width=("relative", 90),
            valign="middle", height=("relative", 70),
        )

    def _add_attachment(self, path):
        import mimetypes
        fname = os.path.basename(path)
        ctype, _ = mimetypes.guess_type(path)
        ctype = ctype or "application/octet-stream"
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.user_attachments.append((fname, ctype, data))
            self._refresh_attach_line()
        except Exception as e:
            self.attach_text.set_text(("status_err", f" Attach error: {e}"))

    def keypress(self, size, key):
        if key == "esc":
            if self._w is not self._box:
                # Picker is open — close it
                self._w = self._box
                return
            urwid.emit_signal(self, "cancel")
            return
        if key == "f2":
            self.pending_to          = self.f_to.edit_text.strip()
            self.pending_subject     = self.f_subject.edit_text.strip()
            self.pending_body        = self.f_body.edit_text
            self.pending_attachments = list(self.user_attachments)
            urwid.emit_signal(self, "send")
            return
        if key == "f3":
            self._open_picker()
            return
        return self._w.keypress(size, key)



# ─────────────────────────────────────────────
# ATTACHMENT LIST DIALOG
# ─────────────────────────────────────────────

class AttachmentItem(urwid.WidgetWrap):
    def __init__(self, info):
        self.info = info
        size_kb = info["size"] / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        dtype = doc_type(info["name"], info["content_type"])
        icon = {"pdf": "[PDF]", "odt": "[ODT]", "docx": "[DOC]"}.get(dtype, "[ATT]")
        line = f" {icon}  {info['name']:<40} {size_str:>10}"
        text = urwid.Text(("msg_normal", line), wrap="clip")
        self._w = urwid.AttrMap(text, "msg_normal", focus_map="msg_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class AttachmentDialog(urwid.WidgetWrap):
    """
    Overlay listing all attachments.
    Keys: Enter = view (PDF) or save, s = save, Esc = close
    """
    signals = ["view_pdf", "save", "close"]

    def __init__(self, attachments):
        self.attachments = attachments
        items = [AttachmentItem(a) for a in attachments]
        if not items:
            items = [urwid.Text(("body_text", "  (no attachments)"))]

        walker = urwid.SimpleFocusListWalker(items)
        listbox = urwid.ListBox(walker)

        hint = urwid.Text(
            [("key_hint", " Enter"), ("status", ":view/save  "),
             ("key_hint", "s"), ("status", ":save  "),
             ("key_hint", "Esc"), ("status", ":close"),
            ]
        )

        pile = urwid.Pile([
            ("weight", 1, listbox),
            ("pack", urwid.AttrMap(urwid.Divider("─"), "divider")),
            ("pack", urwid.AttrMap(hint, "status")),
        ])
        box = urwid.LineBox(pile, title=f"Attachments ({len(attachments)})", title_align="left")
        self._w = box
        self._walker = walker

    def _focused_info(self):
        try:
            w = self._walker.get_focus()[0]
            if hasattr(w, "info"):
                return w.info
        except Exception:
            pass
        return None

    def keypress(self, size, key):
        if key == "esc":
            urwid.emit_signal(self, "close")
            return
        if key in ("enter", "v"):
            self.pending_info = self._focused_info()
            if self.pending_info:
                urwid.emit_signal(self, "view_pdf")
            return
        if key == "f2":
            self.pending_info = self._focused_info()
            if self.pending_info:
                urwid.emit_signal(self, "save")
            return
        return self._w.keypress(size, key)


# ─────────────────────────────────────────────
# TEXT VIEWER DIALOG  (PDF / plain text)
# ─────────────────────────────────────────────

class TextViewerDialog(urwid.WidgetWrap):
    """
    Scrollable text viewer overlay.
    Keys: j/k or arrows = scroll, s = save attachment, Esc = close
    """
    signals = ["save", "close"]

    def __init__(self, title, text, attach_info=None):
        self.attach_info = attach_info
        lines = text.split("\n")
        items = [urwid.Text(("body_text", ln), wrap="space") for ln in lines]
        walker = urwid.SimpleListWalker(items)
        self._listbox = urwid.ListBox(walker)

        can_save = attach_info is not None
        hint_parts = [
            ("key_hint", " ↑↓"), ("status", ":scroll  "),
        ]
        if can_save:
            hint_parts += [("key_hint", "s"), ("status", ":save  ")]
        hint_parts += [("key_hint", "Esc"), ("status", ":close")]

        hint = urwid.Text(hint_parts)
        pile = urwid.Pile([
            ("weight", 1, self._listbox),
            ("pack", urwid.AttrMap(urwid.Divider("─"), "divider")),
            ("pack", urwid.AttrMap(hint, "status")),
        ])
        box = urwid.LineBox(pile, title=title[:60], title_align="left")
        self._w = box

    def keypress(self, size, key):
        if key == "esc":
            urwid.emit_signal(self, "close")
            return
        if key == "s" and self.attach_info:
            urwid.emit_signal(self, "save")
            return
        return self._w.keypress(size, key)




class _FilePickerItem(urwid.WidgetWrap):
    def __init__(self, name, is_dir):
        self.name = name
        self.is_dir = is_dir
        icon = "📁 " if is_dir else "   "
        attr = "body_header" if is_dir else "msg_normal"
        text = urwid.Text((attr, f" {icon}{name}"), wrap="clip")
        self._w = urwid.AttrMap(text, attr, focus_map="msg_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class _FilePicker(urwid.WidgetWrap):
    """
    Inline file picker overlay for ComposeDialog.
    Signals: pick (file selected), cancel
    Navigate: arrows, Enter = open dir / select file, Esc = cancel / go up
    """
    signals = ["pick", "cancel"]

    def __init__(self, start_dir=None):
        self.cwd = os.path.abspath(start_dir or os.path.expanduser("~"))
        self.selected_path = None
        self._walker = urwid.SimpleFocusListWalker([])
        self._listbox = SafeListBox(self._walker)
        self._path_text = urwid.Text(("body_header", ""), wrap="clip")
        self._refresh()

        hint = urwid.Text(
            [("key_hint", " Enter"), ("status", ":open/select  "),
             ("key_hint", "Esc"), ("status", ":up/cancel  "),
             ("key_hint", "Backspace"), ("status", ":up"),
            ]
        )
        pile = urwid.Pile([
            ("pack", urwid.AttrMap(self._path_text, "body_header")),
            ("pack", urwid.AttrMap(urwid.Divider("─"), "divider")),
            ("weight", 1, self._listbox),
            ("pack", urwid.AttrMap(urwid.Divider("─"), "divider")),
            ("pack", urwid.AttrMap(hint, "status")),
        ])
        box = urwid.LineBox(pile, title="Attach file", title_align="left")
        self._w = box

    def _refresh(self):
        self._path_text.set_text(("body_header", f" {self.cwd}"))
        self._walker.clear()
        try:
            entries = sorted(os.listdir(self.cwd))
        except PermissionError:
            self._walker.append(urwid.Text(("status_err", " Permission denied")))
            return
        # Always show . and .. first
        self._walker.append(_FilePickerItem(".", is_dir=True))
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            self._walker.append(_FilePickerItem("..", is_dir=True))
        # Dirs first, then files
        dirs  = [e for e in entries if os.path.isdir(os.path.join(self.cwd, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(self.cwd, e))]
        for d in dirs:
            self._walker.append(_FilePickerItem(d, is_dir=True))
        for f in files:
            self._walker.append(_FilePickerItem(f, is_dir=False))
        if self._walker:
            self._walker.set_focus(0)

    def _go_up(self):
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            self.cwd = parent
            self._refresh()

    def keypress(self, size, key):
        if key == "esc":
            # Go up one dir, or cancel if at root
            parent = os.path.dirname(self.cwd)
            if parent != self.cwd:
                self._go_up()
            else:
                urwid.emit_signal(self, "cancel")
            return
        if key == "backspace":
            self._go_up()
            return
        if key == "enter":
            try:
                widget, _ = self._walker.get_focus()
                if not hasattr(widget, "name"):
                    return
                if widget.name == ".":
                    return  # stay in current dir
                if widget.name == "..":
                    self._go_up()
                    return
                path = os.path.join(self.cwd, widget.name)
                if widget.is_dir:
                    self.cwd = path
                    self._refresh()
                else:
                    self.selected_path = path
                    urwid.emit_signal(self, "pick")
            except Exception:
                pass
            return
        return self._w.keypress(size, key)


class _SentinelRow(urwid.WidgetWrap):
    """Selectable sentinel at bottom of message list — triggers infinite scroll."""
    def __init__(self):
        text = urwid.Text(("loading", "  ↓  scroll for more..."), wrap="clip")
        self._w = urwid.AttrMap(text, "loading", focus_map="msg_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class SafeListBox(urwid.ListBox):
    """
    ListBox koji hvata ListBoxError pri PageUp/PageDown
    kad lista nije dovoljno duga za ekran.
    """
    def keypress(self, size, key):
        try:
            return super().keypress(size, key)
        except Exception:
            return key


# ─────────────────────────────────────────────
# PALETTE
# ─────────────────────────────────────────────

PALETTE = [
    # (name, fg, bg)
    ("header",        "white",       "dark blue"),
    ("header_key",    "yellow",      "dark blue"),
    ("status",        "white",       "dark gray"),
    ("status_err",    "light red",   "dark gray"),
    ("folder_normal", "black",        ""),
    ("folder_focus",  "black",       "light cyan"),
    ("folder_sel",    "white",       "dark blue"),
    ("msg_normal",    "black",        ""),
    ("msg_unread",    "black,bold",   ""),
    ("msg_focus",     "black",       "light cyan"),
    ("msg_unread_focus", "black,bold", "light cyan"),
    ("body_text",     "black",        ""),
    ("body_header",   "dark blue",    ""),
    ("divider",       "black",        ""),
    ("key_hint",      "yellow",      "dark gray"),
    ("loading",       "dark blue",    ""),
    ("compose_bg",          "black",       "light gray"),
    ("compose_label",       "dark blue",   ""),
    ("compose_field",       "black",       "light gray"),
    ("compose_field_focus", "white",       "dark blue"),
]


# ─────────────────────────────────────────────
# WIDGETS
# ─────────────────────────────────────────────

class FolderItem(urwid.WidgetWrap):
    def __init__(self, name, selected=False):
        self.name = name
        attr = "folder_sel" if selected else "folder_normal"
        prefix = "▸ " if selected else "  "
        text = urwid.Text((attr, f"{prefix}{name}"), wrap="clip")
        self._w = urwid.AttrMap(text, attr, focus_map="folder_focus")

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class MessageItem(urwid.WidgetWrap):
    def __init__(self, meta):
        self.meta = meta
        self._build()

    def _build(self):
        uid   = self.meta.get("uid", "")
        subj  = self.meta.get("subject", "")[:55]
        frm   = self.meta.get("from", "")[:25]
        date  = self.meta.get("date", "")
        seen  = self.meta.get("seen", True)

        # Dense single-line: date | from | subject
        line = f" {str(date):>7}  {frm:<26} {subj}"
        normal = "msg_unread" if not seen else "msg_normal"
        focus  = "msg_unread_focus" if not seen else "msg_focus"
        text = urwid.Text((normal, line), wrap="clip")
        self._w = urwid.AttrMap(text, normal, focus_map=focus)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

class MailApp:
    def __init__(self):
        self.config = load_config()
        self.imap = None
        self.current_account = None
        self.current_folder = None
        self.messages = []
        self.page = 1
        self.per_page = 50
        self.status_text = "Welcome to pymail  |  ? = help"
        self.loading = False
        self._loading_more = False   # infinite scroll guard
        self._all_loaded = False     # no more messages on server
        self._current_msg_obj = None  # full email.Message of open message
        self._current_attachments = []
        self._forward_attachments = []  # (fname, ctype, bytes) for Fwd

        self._build_ui()

    # ── UI BUILD ──────────────────────────────

    def _build_ui(self):
        # Header bar
        self.header_left  = urwid.Text(("header", " pymail"), align="left")
        self.header_right = urwid.Text(("header", ""), align="right")
        header = urwid.Columns([
            self.header_left,
            ("pack", self.header_right),
        ])
        self.header_w = urwid.AttrMap(header, "header")

        # Status bar
        self.status_w = urwid.Text(("status", f" {self.status_text}"))
        status_bar = urwid.AttrMap(self.status_w, "status")

        # Key hints bar
        hints = urwid.Text(
            [("key_hint", " Tab"), ("status", ":focus "),
             ("key_hint", "Enter"), ("status", ":open "),
             ("key_hint", "a"), ("status", ":attach "),
             ("key_hint", "m"), ("status", ":compose "),
             ("key_hint", "R"), ("status", ":reply "),
             ("key_hint", "F"), ("status", ":fwd "),
             ("key_hint", "d"), ("status", ":delete "),
             ("key_hint", "r"), ("status", ":refresh "),
             ("key_hint", "c"), ("status", ":connect "),
             ("key_hint", "q"), ("status", ":quit "),
            ],
        )
        hints_bar = urwid.AttrMap(hints, "status")

        # Folder pane
        self.folder_walker = urwid.SimpleFocusListWalker([
            FolderItem("(nije spojeno)")
        ])
        self.folder_list = urwid.ListBox(self.folder_walker)
        folder_box = urwid.LineBox(
            self.folder_list,
            title="Folders",
            title_align="left",
        )

        # Message list pane
        self.msg_walker = urwid.SimpleFocusListWalker([
            urwid.Text(("body_text", "  Select a folder..."))
        ])
        self.msg_list = SafeListBox(self.msg_walker)
        # Infinite scroll — trigger load_more when sentinel row is focused
        urwid.connect_signal(self.msg_walker, "modified", self._on_msg_focus_changed)
        msg_list_box = urwid.LineBox(
            self.msg_list,
            title="Messages",
            title_align="left",
        )

        # Message body pane
        self.body_header_w = urwid.Text(("body_header", ""), wrap="clip")
        self.body_text_w   = urwid.Text(("body_text", ""), wrap="space")
        body_pile = urwid.Pile([
            ("pack", self.body_header_w),
            ("pack", urwid.Divider("─")),
            self.body_text_w,
        ])
        self.body_scroll = urwid.ListBox(urwid.SimpleListWalker([
            self.body_header_w,
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            self.body_text_w,
        ]))
        msg_body_box = urwid.LineBox(
            self.body_scroll,
            title="Body",
            title_align="left",
        )

        # Right column: message list (top) + body (bottom)
        self.right_pile = urwid.Pile([
            ("weight", 40, msg_list_box),
            ("weight", 60, msg_body_box),
        ])

        # Main columns: left (folders) + right
        self.columns = urwid.Columns([
            ("weight", 22, folder_box),
            ("weight", 78, self.right_pile),
        ], dividechars=0)

        # Top-level frame
        self.frame = urwid.Frame(
            body=self.columns,
            header=self.header_w,
            footer=urwid.Pile([
                urwid.AttrMap(self.status_w, "status"),
                hints_bar,
            ]),
        )

        # Focus state: "folders" | "messages" | "body"
        self.focus_panel = "folders"

    # ── STATUS ───────────────────────────────

    def set_status(self, msg, error=False):
        attr = "status_err" if error else "status"
        self.status_w.set_text((attr, f" {msg}"))
        # Trigger a redraw safely — works from both main loop and threads
        if hasattr(self, "loop") and self.loop.screen.started:
            self.loop.set_alarm_in(0, lambda *_: None)

    def set_header(self, account="", folder=""):
        right = f"{account}  {folder} "
        self.header_right.set_text(("header", right))

    # ── FOLDER PANE ──────────────────────────

    def populate_folders(self, folders):
        self.folder_walker.clear()
        for name in folders:
            self.folder_walker.append(FolderItem(name))
        if self.folder_walker:
            self.folder_walker.set_focus(0)

    # ── MESSAGE LIST ─────────────────────────

    def populate_messages(self, messages):
        """Initial load — clears list and populates from scratch."""
        self.messages = list(messages)
        self._all_loaded = len(messages) < self.per_page
        self.msg_walker.clear()
        if not messages:
            self.msg_walker.append(urwid.Text(("body_text", "  (folder is empty)")))
            return
        # Column header (row 0, not selectable)
        hdr = urwid.Text(
            ("body_header", f"  {'Date':>7}  {'From':<26} Subject"),
            wrap="clip"
        )
        self.msg_walker.append(hdr)
        for m in messages:
            self.msg_walker.append(MessageItem(m))
        if not self._all_loaded:
            self._append_load_sentinel()
        if len(self.msg_walker) > 1:
            self.msg_walker.set_focus(1)

    def _append_load_sentinel(self):
        """Sentinel row at bottom — triggers load-more when focused."""
        sentinel = _SentinelRow()
        self.msg_walker.append(sentinel)

    def append_messages(self, new_msgs):
        """Append next page to existing list (infinite scroll)."""
        if not new_msgs:
            self._all_loaded = True
            # Replace sentinel with end-of-list marker
            if self.msg_walker and isinstance(self.msg_walker[-1], _SentinelRow):
                self.msg_walker[-1] = urwid.Text(("body_text", "  — end of folder —"), wrap="clip")
            return
        self._all_loaded = len(new_msgs) < self.per_page
        # Remove sentinel before appending
        if self.msg_walker and isinstance(self.msg_walker[-1], _SentinelRow):
            del self.msg_walker[-1]
        start_idx = len(self.messages)
        self.messages.extend(new_msgs)
        for m in new_msgs:
            self.msg_walker.append(MessageItem(m))
        if not self._all_loaded:
            self._append_load_sentinel()

    def show_message(self, meta, msg_obj):
        """Render full message in body pane."""
        if msg_obj is None:
            self.body_header_w.set_text(("body_header", "  [Fetch error]"))
            self.body_text_w.set_text("")
            return

        frm  = decode_header_str(msg_obj.get("From", ""))
        to   = decode_header_str(msg_obj.get("To", ""))
        subj = decode_header_str(msg_obj.get("Subject", ""))
        date = msg_obj.get("Date", "")

        header_str = (
            f"  From:    {frm}\n"
            f"  To:      {to}\n"
            f"  Date:    {date}\n"
            f"  Subject: {subj}"
        )
        body = get_body(msg_obj)

        att_count = len(list_attachments(msg_obj))
        att_str = f"  [{att_count} attachment{'s' if att_count != 1 else ''}  press 'a']" if att_count else ""
        self.body_header_w.set_text(("body_header", header_str + att_str))

        # Rebuild body scroll list
        new_items = [
            self.body_header_w,
            urwid.AttrMap(urwid.Divider("─"), "divider"),
            urwid.Text(("body_text", body), wrap="space"),
        ]
        self.body_scroll.body[:] = new_items

    # ── IMAP OPERATIONS (threaded) ────────────

    def _run_async(self, fn, *args):
        """Run fn in background thread, schedule redraw on main loop when done."""
        def worker():
            fn(*args)
            # Schedule redraw on main loop — never call draw_screen from a thread
            self.loop.set_alarm_in(0, lambda *_: None)
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def do_connect(self):
        accounts = self.config.get("accounts", [])
        if not accounts:
            self.set_status("No accounts configured in ~/.pymailrc", error=True)
            return
        acc = accounts[0]

        if not acc.get("password"):
            self.set_status("Enter password in ~/.pymailrc", error=True)
            return

        self.set_status(f"Connecting to {acc['imap_host']}...")
        self.imap = IMAPClient(acc)

        def _connect():
            try:
                self.imap.connect()
                folders = self.imap.list_folders()
                # Apply folder_exclude from config
                exclude = set(acc.get("folder_exclude", []))
                if exclude:
                    folders = [f for f in folders if f not in exclude]
                self.current_account = acc["name"]
                self.set_header(acc["name"], "")
                self.populate_folders(folders)
                self.set_status(f"Connected. {len(folders)} folders.")
            except Exception as e:
                self.set_status(f"Connection error: {e}", error=True)
                self.imap = None

        self._run_async(_connect)

    def do_load_folder(self, folder_name):
        if not self.imap:
            self.set_status("Not connected. Press 'c' to connect.", error=True)
            return
        self.current_folder = folder_name
        self.page = 1
        self._all_loaded = False
        self._loading_more = False
        self.set_status(f"Loading {folder_name}...")
        self.set_header(self.current_account or "", folder_name)

        def _load():
            try:
                msgs = self.imap.fetch_headers(folder_name, 1, self.per_page)
                self.populate_messages(msgs)
                total = len(msgs)
                suffix = "+" if not self._all_loaded else ""
                self.set_status(f"{folder_name}: {total}{suffix} messages")
            except Exception as e:
                self.set_status(f"Error: {e}", error=True)

        self._run_async(_load)

    def do_load_more(self):
        """Load next page and append (called when sentinel focused)."""
        if self._loading_more or self._all_loaded or not self.imap:
            return
        self._loading_more = True
        self.page += 1
        folder = self.current_folder

        def _load():
            try:
                msgs = self.imap.fetch_headers(folder, self.page, self.per_page)
                self.append_messages(msgs)
                total = len(self.messages)
                suffix = "+" if not self._all_loaded else ""
                self.set_status(f"{folder}: {total}{suffix} messages loaded")
            except Exception as e:
                self.set_status(f"Load more error: {e}", error=True)
            finally:
                self._loading_more = False

        self._run_async(_load)

    def do_open_message(self, idx):
        """idx is index in self.messages list."""
        if idx < 0 or idx >= len(self.messages):
            return
        meta = self.messages[idx]
        uid = meta.get("uid")
        if uid is None:
            return
        self.set_status(f"Loading message {uid}...")

        def _load():
            try:
                msg_obj = self.imap.fetch_message(uid)
                self.imap.mark_seen(uid)
                # Update seen flag in list
                self.messages[idx]["seen"] = True
                self._current_msg_obj = msg_obj
                self._current_attachments = list_attachments(msg_obj)
                self.show_message(meta, msg_obj)
                self.set_status(
                    f"From: {meta.get('from','')[:60]}  |  {meta.get('subject','')[:60]}"
                )
            except Exception as e:
                self.set_status(f"Open error: {e}", error=True)

        self._run_async(_load)

    # ── COMPOSE / REPLY ─────────────────────────

    def do_compose(self, to="", subject="", body="", reply_msg=None, forward_attachments=None):
        """Open compose dialog as overlay."""
        dlg = ComposeDialog(to=to, subject=subject, body=body)
        self._reply_msg = reply_msg
        self._forward_attachments = forward_attachments or []

        def on_send():
            to_addr   = getattr(dlg, "pending_to", "").strip()
            subj      = getattr(dlg, "pending_subject", "").strip()
            body_text = getattr(dlg, "pending_body", "")
            # Merge user-added attachments + forward attachments
            user_atts = getattr(dlg, "pending_attachments", [])
            all_atts  = list(self._forward_attachments) + list(user_atts)
            self._close_overlay()
            if not to_addr:
                self.set_status("Error: 'To' field is empty.", error=True)
                return
            recipients = [a.strip() for a in to_addr.split(",") if a.strip()]
            self.set_status(f"Sending to {', '.join(recipients)}...")
            cfg = self.current_account_cfg()
            if not cfg:
                self.set_status("No account configured.", error=True)
                return
            smtp = SMTPClient(cfg)
            reply_msg = self._reply_msg
            def _send():
                try:
                    smtp.send(
                        recipients, subj, body_text,
                        reply_to=reply_msg,
                        attachments=all_atts if all_atts else None,
                    )
                    self.set_status(f"Sent → {', '.join(recipients)}")
                except Exception as e:
                    self.set_status(f"Send error: {e}", error=True)
            self._run_async(_send)

        def on_cancel():
            self._close_overlay()
            self.set_status("Compose cancelled.")

        urwid.connect_signal(dlg, "send",   on_send)
        urwid.connect_signal(dlg, "cancel", on_cancel)

        overlay = urwid.Overlay(
            dlg, self.frame,
            align="center", width=("relative", 90),
            valign="middle", height=("relative", 80),
        )
        self.loop.widget = overlay

    # ── ATTACHMENTS ──────────────────────────────

    def do_attachments(self):
        """Show attachment list overlay for current message."""
        if not self._current_msg_obj:
            self.set_status("No message open.", error=True)
            return
        attachments = self._current_attachments
        if not attachments:
            self.set_status("No attachments in this message.")
            return

        dlg = AttachmentDialog(attachments)

        def on_view():
            info = getattr(dlg, "pending_info", None)
            self._close_overlay()
            if info:
                self._open_attachment_viewer(info)

        def on_save():
            info = getattr(dlg, "pending_info", None)
            if info:
                self._do_save_attachment(info)

        def on_close():
            self._close_overlay()

        urwid.connect_signal(dlg, "view_pdf", on_view)
        urwid.connect_signal(dlg, "save",     on_save)
        urwid.connect_signal(dlg, "close",    on_close)

        overlay = urwid.Overlay(
            dlg, self.loop.widget,
            align="center", width=("relative", 80),
            valign="middle", height=("relative", 60),
        )
        self.loop.widget = overlay

    def _open_attachment_viewer(self, info):
        """View attachment — PDF/ODT/DOCX get text extracted, others show info."""
        name  = info["name"]
        ct    = info["content_type"]
        dtype = doc_type(name, ct)

        extractors = {
            "pdf":  (pdf_to_text,  "PDF"),
            "odt":  (odt_to_text,  "ODT"),
            "docx": (docx_to_text, "DOC"),
        }

        # Plain text — show content directly
        is_text = ct.startswith("text/") or name.lower().endswith(
            (".txt", ".csv", ".log", ".md", ".py", ".sh", ".json", ".xml", ".html", ".ini", ".cfg")
        )

        if dtype in extractors:
            fn, label = extractors[dtype]
            self.set_status(f"Extracting text from {name}...")
            def _extract(fn=fn, label=label):
                payload = info["part"].get_payload(decode=True) or b""
                text = fn(payload)
                self._show_text_viewer(f"{label}: {name}", text, info)
            self._run_async(_extract)
        elif is_text:
            self.set_status(f"Loading {name}...")
            def _load_text():
                payload = info["part"].get_payload(decode=True) or b""
                charset = info["part"].get_content_charset() or "utf-8"
                try:
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = payload.decode("latin-1", errors="replace")
                self._show_text_viewer(f"Text: {name}", text, info)
            self._run_async(_load_text)
        else:
            size_kb = info["size"] / 1024
            text = (
                f"File:  {name}\n"
                f"Type:  {ct}\n"
                f"Size:  {size_kb:.1f} KB\n\n"
                f"Press 's' to save to attachments/\n"
                f"Press Esc to close."
            )
            self._show_text_viewer(f"Attachment: {name}", text, info)

    def _show_text_viewer(self, title, text, attach_info=None):
        """Open TextViewerDialog overlay."""
        dlg = TextViewerDialog(title, text, attach_info)

        def on_save():
            self._do_save_attachment(dlg.attach_info)

        def on_close():
            self._close_overlay()

        urwid.connect_signal(dlg, "save",  on_save)
        urwid.connect_signal(dlg, "close", on_close)

        overlay = urwid.Overlay(
            dlg, self.frame,
            align="center", width=("relative", 92),
            valign="middle", height=("relative", 88),
        )
        self.loop.widget = overlay

    def _do_save_attachment(self, info):
        """Save attachment to disk in background thread."""
        def _save():
            try:
                path = save_attachment(info)
                self.set_status(f"Saved: {path}")
            except Exception as e:
                self.set_status(f"Save error: {e}", error=True)
        self._run_async(_save)

    def _close_overlay(self):
        self.loop.widget = self.frame

    def current_account_cfg(self):
        accounts = self.config.get("accounts", [])
        return accounts[0] if accounts else None

    def do_reply(self):
        """Reply to the currently open message with quoted body."""
        if not self._current_msg_obj:
            self.set_status("No open message to reply to.", error=True)
            return
        msg  = self._current_msg_obj
        frm  = decode_header_str(msg.get("From", ""))
        date = msg.get("Date", "")
        subj = decode_header_str(msg.get("Subject", ""))

        if not subj.lower().startswith("re:"):
            subj = "Re: " + subj

        # Quoted body — standard "> " prefix per line
        original_body = get_body(msg)
        quoted = "\n".join(f"> {line}" for line in original_body.splitlines())
        reply_body = f"\n\nOn {date}, {frm} wrote:\n{quoted}"

        self.do_compose(to=frm, subject=subj, body=reply_body, reply_msg=msg)

    # ── FORWARD ──────────────────────────────────

    def do_forward(self):
        """Forward currently open message with quoted body and all attachments."""
        if not self._current_msg_obj:
            self.set_status("No open message to forward.", error=True)
            return
        msg = self._current_msg_obj

        # Build quoted header block
        frm  = decode_header_str(msg.get("From", ""))
        to   = decode_header_str(msg.get("To", ""))
        date = msg.get("Date", "")
        subj = decode_header_str(msg.get("Subject", ""))

        quoted_header = (
            "\n\n-------- Forwarded Message --------\n"
            f"From:    {frm}\n"
            f"Date:    {date}\n"
            f"Subject: {subj}\n"
            f"To:      {to}\n"
            "\n"
        )
        original_body = get_body(msg)
        fwd_body = quoted_header + original_body

        # Prefix subject
        fwd_subj = subj
        if not fwd_subj.lower().startswith("fwd:") and not fwd_subj.lower().startswith("fw:"):
            fwd_subj = "Fwd: " + fwd_subj

        # Collect attachments as (filename, content_type, bytes)
        fwd_attachments = []
        for att in self._current_attachments:
            payload = att["part"].get_payload(decode=True)
            if payload:
                fwd_attachments.append((att["name"], att["content_type"], payload))

        att_note = f"  [{len(fwd_attachments)} attachment(s) will be forwarded]" if fwd_attachments else ""
        self.set_status(f"Forward: {fwd_subj}{att_note}")
        self.do_compose(subject=fwd_subj, body=fwd_body, forward_attachments=fwd_attachments)

    # ── DELETE ──────────────────────────────────

    def do_delete(self):
        """Mark current message as deleted and expunge."""
        if not self._current_msg_obj:
            self.set_status("No open message to delete.", error=True)
            return
        if not self.imap:
            self.set_status("Not connected.", error=True)
            return

        # Find UID of currently displayed message
        uid = None
        try:
            pos = self.msg_list.focus_position
            msg_idx = pos - 1
            if 0 <= msg_idx < len(self.messages):
                uid = self.messages[msg_idx].get("uid")
        except Exception:
            pass

        if uid is None:
            self.set_status("Cannot determine message UID.", error=True)
            return

        folder = self.current_folder
        msg_idx_to_remove = None
        try:
            pos = self.msg_list.focus_position
            msg_idx_to_remove = pos - 1
        except Exception:
            pass

        self.set_status(f"Deleting message {uid}...")

        def _delete():
            try:
                self.imap.conn.store(str(uid), "+FLAGS", "\\Deleted")
                self.imap.conn.expunge()
                # Remove from local list and walker
                if msg_idx_to_remove is not None and 0 <= msg_idx_to_remove < len(self.messages):
                    self.messages.pop(msg_idx_to_remove)
                    walker_pos = msg_idx_to_remove + 1  # +1 for header row
                    if walker_pos < len(self.msg_walker):
                        del self.msg_walker[walker_pos]
                # Clear body pane
                self.body_header_w.set_text(("body_header", ""))
                self.body_scroll.body[:] = [self.body_header_w]
                self._current_msg_obj = None
                self._current_attachments = []
                self.set_status(f"Deleted. {len(self.messages)} messages remaining.")
            except Exception as e:
                self.set_status(f"Delete error: {e}", error=True)

        self._run_async(_delete)

    # ── KEY HANDLING ─────────────────────────

    def unhandled_input(self, key):
        if key in ("q", "Q"):
            if self.imap:
                self.imap.disconnect()
            raise urwid.ExitMainLoop()

        elif key == "c":
            self.do_connect()

        elif key == "r":
            if self.current_folder:
                self.do_load_folder(self.current_folder)
            elif self.imap:
                self.do_connect()

        elif key == "tab":
            self._cycle_focus()

        elif key == "enter":
            self._handle_enter()

        elif key == "a":
            self.do_attachments()

        elif key in ("m", "M"):
            self.do_compose()

        elif key in ("R",):
            self.do_reply()

        elif key == "F":
            self.do_forward()

        elif key == "d":
            self.do_delete()

        elif key == "?":
            self.set_status(
                "Tab:focus  Enter:open  c:connect  r:refresh  "
                "m:compose  R:reply  F:fwd  d:delete  q:quit"
            )

    def _cycle_focus(self):
        if self.focus_panel == "folders":
            self.focus_panel = "messages"
            self.columns.focus_position = 1
            self.right_pile.focus_position = 0
        elif self.focus_panel == "messages":
            self.focus_panel = "body"
            self.columns.focus_position = 1
            self.right_pile.focus_position = 1
        else:
            self.focus_panel = "folders"
            self.columns.focus_position = 0

    def _on_msg_focus_changed(self):
        """Called whenever message list focus changes — check if sentinel reached."""
        try:
            widget, pos = self.msg_walker.get_focus()
            if isinstance(widget, _SentinelRow) and not self._loading_more and not self._all_loaded:
                self.do_load_more()
        except Exception:
            pass

    def _handle_enter(self):
        if self.focus_panel == "folders":
            # Open selected folder
            try:
                pos = self.folder_list.focus_position
                widget = self.folder_walker[pos]
                if hasattr(widget, "name"):
                    self.page = 1
                    self.do_load_folder(widget.name)
                    # Switch focus to message list
                    self.focus_panel = "messages"
                    self.columns.focus_position = 1
                    self.right_pile.focus_position = 0
            except Exception:
                pass

        elif self.focus_panel == "messages":
            try:
                pos = self.msg_list.focus_position
                # pos 0 = header, last pos = sentinel (if not all loaded)
                widget = self.msg_walker[pos]
                is_sentinel = isinstance(widget, _SentinelRow)
                msg_idx = pos - 1
                if msg_idx >= 0 and not is_sentinel:
                    self.do_open_message(msg_idx)
                    self.focus_panel = "body"
                    self.right_pile.focus_position = 1
            except Exception:
                pass

    # ── RUN ──────────────────────────────────

    def run(self):
        self.loop = urwid.MainLoop(
            self.frame,
            palette=PALETTE,
            unhandled_input=self.unhandled_input,
        )
        self.loop.set_alarm_in(0, lambda *_: self.set_status(
            "Press 'c' to connect  |  ? = help  |  q = quit"
        ))
        self.loop.run()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = MailApp()
    app.run()
