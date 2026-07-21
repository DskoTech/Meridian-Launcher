"""display_audio_server.py — "Display & Audio" plug-on (System section).

One controller-friendly panel for resolution, refresh rate, HDR, and
audio output device - the things people actually reach for from the
couch, without diving into Windows Settings with a gamepad-to-mouse
cursor. Same loopback-only, in-process pattern as task_manager_server.py:
runs in Meridian Launcher's own process and calls display_settings.py /
audio_devices.py directly, no subprocess.

CONTROLLER-FIRST LAYOUT: every control is a single flat list of large
focusable buttons - Up/Down moves between ALL of them (resolutions,
refresh rates, the HDR toggle, audio devices, in that order), Enter/A
applies whichever one is focused. A flat list rather than a 2D grid
(unlike task_manager_server.py's Focus/Close columns) on purpose: there's
only one action per control here ("pick this"), so there's no second
column to navigate to - keeping it a single axis is simpler to drive
with a d-pad than it would be to justify a second dimension for.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import display_settings
import audio_devices

IS_WINDOWS = sys.platform == "win32"

# Fixed rather than OS-assigned - see task_manager_server.py's
# DEFAULT_PORT docstring for why. A different port than the other two
# System/Apps plug-ons so all three can run at once.
DEFAULT_PORT = 58736

_state = {"httpd": None, "port": None}

_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Display &amp; Audio — Meridian Launcher</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; padding:22px; background:#0b1410; color:#eafff0; font-family:system-ui,sans-serif; }
  h1 { font-size:20px; color:#7CFFB2; margin:0 0 4px; }
  .sub { font-size:13px; color:#8aa; margin:0 0 18px; }
  h2 { font-size:14px; color:#8aa; text-transform:uppercase; letter-spacing:.06em; margin:22px 0 8px; }
  .grid { display:flex; flex-wrap:wrap; gap:10px; }
  button.opt {
    font-size:15px; font-weight:600; padding:12px 18px; border-radius:10px; border:2px solid #1e3327;
    background:#111f18; color:#eafff0; cursor:pointer; min-width:120px;
  }
  button.opt .small { display:block; font-size:11px; font-weight:400; color:#8aa; margin-top:3px; font-family:monospace; }
  button.opt.active { border-color:#7CFFB2; background:#17321f; color:#7CFFB2; }
  button.opt:focus-visible { outline:none; border-color:#7CFFB2; box-shadow:0 0 0 3px rgba(124,255,178,0.35); }
  .empty { color:#8aa; font-size:13px; }
  .status { font-size:12px; color:#8aa; margin-top:16px; min-height:16px; }
</style></head>
<body>
  <h1>Display &amp; Audio</h1>
  <p class="sub">Up/Down between options, A/Enter to apply.</p>

  <h2>Resolution</h2>
  <div class="grid" id="res-list"><div class="empty">Loading&hellip;</div></div>

  <h2>Refresh Rate</h2>
  <div class="grid" id="rate-list"><div class="empty">Pick a resolution first.</div></div>

  <h2>HDR</h2>
  <div class="grid" id="hdr-list"><div class="empty">Loading&hellip;</div></div>

  <h2>Audio Output</h2>
  <div class="grid" id="audio-list"><div class="empty">Loading&hellip;</div></div>

  <div class="status" id="status"></div>

<script>
let data = { modes: [], current: null, hdr: null, audio: [] };
let selectedRes = null; // {width, height}
let focusables = [];    // flat, in DOM order — rebuilt after every render
let idx = 0;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}
function setStatus(msg) {
  const s = document.getElementById("status");
  s.textContent = msg;
  if (msg) setTimeout(() => { if (s.textContent === msg) s.textContent = ""; }, 2000);
}

function renderResolutions() {
  const el = document.getElementById("res-list");
  if (!data.modes.length) { el.innerHTML = '<div class="empty">No resolutions reported.</div>'; return; }
  el.innerHTML = "";
  data.modes.forEach((m) => {
    const isCurrent = data.current && data.current.width === m.width && data.current.height === m.height;
    if (!selectedRes && isCurrent) selectedRes = { width: m.width, height: m.height };
    const b = document.createElement("button");
    b.className = "opt" + (isCurrent ? " active" : "");
    b.textContent = `${m.width} × ${m.height}`;
    b.addEventListener("click", () => { selectedRes = { width: m.width, height: m.height }; renderRefreshRates(); rebuildFocus(); });
    el.appendChild(b);
  });
}

function renderRefreshRates() {
  const el = document.getElementById("rate-list");
  if (!selectedRes) { el.innerHTML = '<div class="empty">Pick a resolution first.</div>'; return; }
  const mode = data.modes.find((m) => m.width === selectedRes.width && m.height === selectedRes.height);
  const rates = mode ? mode.refresh_rates : [];
  if (!rates.length) { el.innerHTML = '<div class="empty">No refresh rates reported.</div>'; return; }
  el.innerHTML = "";
  rates.forEach((hz) => {
    const isCurrent = data.current && data.current.width === selectedRes.width && data.current.height === selectedRes.height && data.current.refresh_rate === hz;
    const b = document.createElement("button");
    b.className = "opt" + (isCurrent ? " active" : "");
    b.textContent = `${hz} Hz`;
    b.addEventListener("click", async () => {
      setStatus("Applying...");
      const res = await fetch(`/set_display_mode?w=${selectedRes.width}&h=${selectedRes.height}&hz=${hz}`, { method: "POST" });
      const j = await res.json();
      setStatus(j.ok ? "Applied." : `Couldn't apply: ${j.error || "unknown error"}`);
      if (j.ok) refresh();
    });
    el.appendChild(b);
  });
}

function renderHdr() {
  const el = document.getElementById("hdr-list");
  const h = data.hdr;
  if (!h || !h.ok) { el.innerHTML = `<div class="empty">${escapeHtml((h && h.error) || "HDR state unavailable.")}</div>`; return; }
  if (!h.supported) { el.innerHTML = '<div class="empty">This display doesn\\'t report HDR support.</div>'; return; }
  el.innerHTML = "";
  [["On", true], ["Off", false]].forEach(([label, val]) => {
    const b = document.createElement("button");
    b.className = "opt" + (h.enabled === val ? " active" : "");
    b.textContent = label;
    b.addEventListener("click", async () => {
      setStatus("Applying...");
      const res = await fetch(`/set_hdr?enable=${val ? "1" : "0"}`, { method: "POST" });
      const j = await res.json();
      setStatus(j.ok ? "Applied." : `Couldn't apply: ${j.error || "unknown error"}`);
      if (j.ok) refresh();
    });
    el.appendChild(b);
  });
}

function renderAudio() {
  const el = document.getElementById("audio-list");
  if (!data.audio.length) { el.innerHTML = '<div class="empty">No active playback devices found.</div>'; return; }
  el.innerHTML = "";
  data.audio.forEach((d) => {
    const b = document.createElement("button");
    b.className = "opt" + (d.is_default ? " active" : "");
    b.innerHTML = `${escapeHtml(d.name)}${d.is_default ? '<span class="small">Default</span>' : ""}`;
    b.addEventListener("click", async () => {
      setStatus("Switching...");
      const res = await fetch(`/set_audio_device?id=${encodeURIComponent(d.id)}`, { method: "POST" });
      const j = await res.json();
      setStatus(j.ok ? "Switched." : `Couldn't switch: ${j.error || "unknown error"}`);
      if (j.ok) refresh();
    });
    el.appendChild(b);
  });
}

function rebuildFocus() {
  focusables = Array.from(document.querySelectorAll("button.opt"));
  idx = Math.max(0, Math.min(idx, focusables.length - 1));
  if (focusables[idx]) focusables[idx].focus();
}

function renderAll() {
  renderResolutions();
  renderRefreshRates();
  renderHdr();
  renderAudio();
  rebuildFocus();
}

async function refresh() {
  try {
    const [modesRes, hdrRes, audioRes] = await Promise.all([
      fetch("/display_modes.json").then((r) => r.json()),
      fetch("/hdr_state.json").then((r) => r.json()),
      fetch("/audio_devices.json").then((r) => r.json()),
    ]);
    data.modes = modesRes.modes || [];
    data.current = modesRes.current || null;
    data.hdr = hdrRes;
    data.audio = audioRes.devices || [];
  } catch (e) { /* leave stale data on screen rather than blanking it */ }
  renderAll();
}

document.addEventListener("keydown", (e) => {
  if (!focusables.length) return;
  if (e.key === "ArrowDown" || e.key === "ArrowRight") { idx = Math.min(idx + 1, focusables.length - 1); focusables[idx].focus(); e.preventDefault(); }
  else if (e.key === "ArrowUp" || e.key === "ArrowLeft") { idx = Math.max(idx - 1, 0); focusables[idx].focus(); e.preventDefault(); }
});

refresh();
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _send_json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_html(self):
        data = _PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_html()
            return
        if parsed.path == "/display_modes.json":
            self._send_json(display_settings.list_display_modes())
            return
        if parsed.path == "/hdr_state.json":
            self._send_json(display_settings.get_hdr_state())
            return
        if parsed.path == "/audio_devices.json":
            try:
                err = audio_devices.import_error()
                if err is not None:
                    self._send_json({"ok": False, "devices": [], "error": "Audio Output unavailable: " + err})
                else:
                    devices = audio_devices.list_output_devices()
                    self._send_json({"ok": True, "devices": devices, "error": None})
            except Exception as e:
                self._send_json({"ok": False, "devices": [], "error": str(e)})
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/set_display_mode":
            try:
                w, h, hz = int(qs["w"][0]), int(qs["h"][0]), int(qs["hz"][0])
            except Exception:
                self._send_json({"ok": False, "error": "Bad parameters."})
                return
            self._send_json(display_settings.set_display_mode(w, h, hz))
            return
        if parsed.path == "/set_hdr":
            enable = qs.get("enable", ["0"])[0] == "1"
            self._send_json(display_settings.set_hdr_state(enable))
            return
        if parsed.path == "/set_audio_device":
            device_id = qs.get("id", [None])[0]
            if not device_id:
                self._send_json({"ok": False, "error": "No device id."})
                return
            self._send_json(audio_devices.set_default_output_device(device_id))
            return
        self.send_error(404)


def start_server():
    """Starts the server once (idempotent). Returns {"port": int|None}."""
    if _state["httpd"] is not None:
        return {"port": _state["port"]}
    httpd = None
    for port in (DEFAULT_PORT, 0):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            break
        except OSError:
            continue
    if httpd is None:
        return {"port": None}
    _state["httpd"] = httpd
    _state["port"] = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return {"port": _state["port"]}
