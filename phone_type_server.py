"""phone_type_server.py — "Type from Phone" plug-on (Apps section).

Long passwords, search terms, and chat messages are painful to click out
one character at a time on the on-screen keyboard from a couch with a
controller. This runs a tiny local web server so a phone on the same
Wi-Fi can type instead: point a phone's camera at a QR code shown on the
TV/monitor, type on the phone's own keyboard, hit Send, and the text
gets injected as real keystrokes on the PC via the `keyboard` package —
landing wherever focus currently is (a password field, the browser's
address bar, a chat box), exactly like typing it by hand would.

Two pages, same server:
  GET /display       - shown ON THE PC (boxed into NetBrowse by the
                        plug-on's own plugin.json "url") - the QR code,
                        the URL as text, and a "waiting for a phone to
                        connect" style status line.
  GET /type?t=<TOKEN> - shown ON THE PHONE after scanning - a plain
                        textarea + Send button, sized for a touchscreen.
  POST /type          - phone page's Send button posts here; the body is
                        injected as keystrokes and the endpoint clears
                        the field for the next message.

SECURITY NOTE: this is intentionally simple, not hardened. The random
per-launch token in the QR code stops someone on the same Wi-Fi from
finding /type by guessing the URL, but this is plaintext HTTP with no
pairing/approval step beyond "you scanned the code" - fine for a home
network, not something to expose past a router. The server only ever
acts on a POST that carries the correct token; GET /display and the QR
image itself are the only unauthenticated routes, and they reveal
nothing but the (already-token-bearing) phone-page URL.
"""

import html
import json
import socket
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import urlparse, parse_qs

IS_WINDOWS = sys.platform == "win32"

# Fixed rather than OS-assigned: the plug-on's plugin.json points at this
# port by name (a static manifest can't know a randomly-chosen port
# ahead of time). Falls back to an OS-assigned port only if this one is
# somehow already taken - see start_server()'s docstring.
DEFAULT_PORT = 58734

_state = {
    "token": None,
    "port": None,
    "lan_ip": None,
    "httpd": None,
    "last_connected": False,  # a phone has hit /type (GET) at least once
}
_keyboard_lock = threading.Lock()


def _lan_ip():
    """Best-effort LAN IP (not loopback) for the QR code to point phones
    at. The UDP "connect" here never actually sends a packet - it just
    asks the OS which local interface/IP would be used to reach that
    address, which is the standard no-traffic trick for this."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


def _inject_text(text):
    if not text:
        return
    try:
        import keyboard
    except ImportError:
        return
    with _keyboard_lock:
        try:
            keyboard.write(text)
        except Exception:
            pass


_PHONE_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Type from Phone — Meridian Launcher</title>
<style>
  body {{ margin:0; padding:16px; background:#0b1410; color:#eafff0; font-family:system-ui,sans-serif; }}
  h1 {{ font-size:16px; font-weight:600; margin:0 0 12px; color:#7CFFB2; }}
  textarea {{ width:100%; box-sizing:border-box; min-height:140px; font-size:17px; padding:12px;
    border-radius:10px; border:1px solid #244; background:#0f1c16; color:#eafff0; resize:vertical; }}
  button {{ width:100%; margin-top:12px; padding:16px; font-size:17px; font-weight:600;
    border-radius:10px; border:1px solid #7CFFB2; background:#123322; color:#7CFFB2; }}
  button:active {{ background:#1c4a30; }}
  .hint {{ font-size:12px; color:#8aa; margin-top:10px; }}
  .status {{ font-size:13px; margin-top:14px; min-height:16px; }}
</style></head>
<body>
  <h1>Type from Phone</h1>
  <textarea id="txt" autofocus placeholder="Type here, then hit Send. It'll type into whatever's focused on the PC."></textarea>
  <button id="send">Send</button>
  <div class="hint">Newlines send Enter on the PC side too — handy for chat, not for passwords.</div>
  <div class="status" id="status"></div>
  <script>
    const txt = document.getElementById("txt");
    const status = document.getElementById("status");
    document.getElementById("send").addEventListener("click", async () => {{
      const text = txt.value;
      if (!text) return;
      status.textContent = "Sending...";
      try {{
        const res = await fetch("/type?t={token}", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ text }}),
        }});
        if (res.ok) {{ txt.value = ""; status.textContent = "Sent."; txt.focus(); }}
        else {{ status.textContent = "Couldn't send (bad link? try rescanning the QR code)."; }}
      }} catch (e) {{ status.textContent = "Couldn't reach the PC — same Wi-Fi?"; }}
      setTimeout(() => {{ status.textContent = ""; }}, 1500);
    }});
  </script>
</body></html>"""

_DISPLAY_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Type from Phone</title>
<style>
  body {{ margin:0; height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center;
    background:#0b1410; color:#eafff0; font-family:system-ui,sans-serif; text-align:center; }}
  h1 {{ font-size:22px; color:#7CFFB2; margin:0 0 6px; }}
  p {{ color:#8aa; font-size:14px; margin:0 0 20px; }}
  img {{ background:#fff; padding:14px; border-radius:12px; }}
  .url {{ margin-top:16px; font-family:monospace; font-size:13px; color:#7CFFB2; word-break:break-all; padding:0 24px; }}
</style></head>
<body>
  <h1>Type from Phone</h1>
  <p>Scan with your phone's camera, then type there.</p>
  <img src="/qr.png?t={token}" width="260" height="260" alt="QR code">
  <div class="url">{url}</div>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _send_html(self, body, code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _valid_token(self, qs):
        return qs.get("t", [None])[0] == _state["token"]

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/display":
            url = _phone_url()
            self._send_html(_DISPLAY_PAGE.format(token=html.escape(_state["token"] or ""), url=html.escape(url)))
            return
        if parsed.path == "/type":
            qs = parse_qs(parsed.query)
            if not self._valid_token(qs):
                self.send_error(403, "Bad or missing link — rescan the QR code.")
                return
            _state["last_connected"] = True
            self._send_html(_PHONE_PAGE.format(token=html.escape(_state["token"] or "")))
            return
        if parsed.path == "/qr.png":
            qs = parse_qs(parsed.query)
            if not self._valid_token(qs):
                self.send_error(403)
                return
            png = _qr_png_bytes(_phone_url())
            if png is None:
                self.send_error(500, "QR generation unavailable (qrcode/Pillow not installed).")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            try:
                self.wfile.write(png)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/type":
            self.send_error(404)
            return
        qs = parse_qs(parsed.query)
        if not self._valid_token(qs):
            self.send_error(403, "Bad or missing link — rescan the QR code.")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            text = payload.get("text", "")
        except Exception:
            self.send_error(400)
            return
        _inject_text(text)
        self._send_html("ok")


def _phone_url():
    return f"http://{_state['lan_ip']}:{_state['port']}/type?t={_state['token']}"


def _qr_png_bytes(data):
    try:
        import qrcode
    except ImportError:
        return None
    try:
        img = qrcode.make(data)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def start_server():
    """Starts the server once (idempotent - safe to call every launch).
    Returns {"port", "lan_ip", "token"}."""
    if _state["httpd"] is not None:
        return {"port": _state["port"], "lan_ip": _state["lan_ip"], "token": _state["token"]}

    _state["token"] = secrets.token_urlsafe(16)
    _state["lan_ip"] = _lan_ip()

    httpd = None
    for port in (DEFAULT_PORT, 0):  # try the fixed port first, OS-assigned as a fallback
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
            break
        except OSError:
            continue
    if httpd is None:
        return {"port": None, "lan_ip": _state["lan_ip"], "token": _state["token"]}

    _state["httpd"] = httpd
    _state["port"] = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return {"port": _state["port"], "lan_ip": _state["lan_ip"], "token": _state["token"]}


def status():
    return {
        "running": _state["httpd"] is not None,
        "port": _state["port"],
        "lan_ip": _state["lan_ip"],
        "phone_connected": _state["last_connected"],
    }
