"""network_pairing_server.py — "Wi-Fi & Bluetooth" plug-on (System
section). A controller-navigable scan-and-pair replacement for the old
native network-overlay: real Wi-Fi network names/signal (via
system_actions.wifi_scan, unchanged - that part already worked), an
on-screen keyboard for WPA passwords (so a password never has to be
clicked out one character at a time), and real Bluetooth scan+pair
(bluetooth_pairing.py) instead of just toggling already-known devices.

Same loopback-only, in-process pattern as the other System/Apps
plug-ins: runs in Meridian Launcher's own process and calls
system_actions.py / bluetooth_pairing.py directly.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import system_actions
import bluetooth_pairing

IS_WINDOWS = sys.platform == "win32"

# Fixed rather than OS-assigned - see task_manager_server.py's
# DEFAULT_PORT docstring for why. A different port than the other
# System/Apps plug-ons so all four can run at once.
DEFAULT_PORT = 58737

_state = {"httpd": None, "port": None}

_PAGE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Wi-Fi &amp; Bluetooth — Meridian Launcher</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; padding:22px; background:#0b1410; color:#eafff0; font-family:system-ui,sans-serif; }
  h1 { font-size:20px; color:#7CFFB2; margin:0 0 4px; }
  .sub { font-size:13px; color:#8aa; margin:0 0 18px; }
  h2 { font-size:14px; color:#8aa; text-transform:uppercase; letter-spacing:.06em; margin:22px 0 8px; display:flex; align-items:center; gap:10px; }
  h2 button.scan { font-size:11px; text-transform:none; letter-spacing:0; padding:5px 10px; }
  .list { display:flex; flex-direction:column; gap:8px; }
  .row {
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    background:#111f18; border:1px solid #1e3327; border-radius:10px; padding:10px 14px;
  }
  .row .name { font-size:14px; font-weight:600; }
  .row .meta { font-size:11px; color:#8aa; font-family:monospace; margin-top:2px; }
  button { font-size:14px; font-weight:600; padding:9px 16px; border-radius:8px; border:2px solid #1e3327;
    background:#17281f; color:#eafff0; cursor:pointer; }
  button.primary { border-color:#7CFFB2; color:#7CFFB2; }
  button:focus-visible { outline:none; border-color:#7CFFB2; box-shadow:0 0 0 3px rgba(124,255,178,0.35); }
  .empty { color:#8aa; font-size:13px; padding:6px 0; }
  .status { font-size:12px; color:#8aa; margin-top:16px; min-height:16px; }

  #kbd-overlay {
    position:fixed; inset:0; background:rgba(4,8,6,0.92); display:flex; align-items:center; justify-content:center;
  }
  #kbd-overlay.hidden { display:none; }
  .kbd-box { background:#0f1c16; border:1px solid #244; border-radius:14px; padding:20px; width:min(560px, 92vw); }
  .kbd-title { font-size:14px; color:#8aa; margin-bottom:8px; }
  .kbd-field { font-family:monospace; font-size:18px; background:#0b1410; border:1px solid #1e3327; border-radius:8px;
    padding:12px; min-height:20px; margin-bottom:14px; letter-spacing:2px; word-break:break-all; }
  .kbd-rows { display:flex; flex-direction:column; gap:6px; }
  .kbd-row { display:flex; gap:6px; justify-content:center; }
  .kbd-key { min-width:34px; padding:10px 6px; text-align:center; font-family:monospace; }
  .kbd-key.wide { min-width:70px; }
</style></head>
<body>
  <h1>Wi-Fi &amp; Bluetooth</h1>
  <p class="sub">Up/Down between options, A/Enter to apply.</p>

  <h2>Wi-Fi Networks <button class="scan" id="wifi-scan">Rescan</button></h2>
  <div class="list" id="wifi-list"><div class="empty">Loading&hellip;</div></div>

  <h2>Paired Bluetooth Devices</h2>
  <div class="list" id="bt-paired-list"><div class="empty">Loading&hellip;</div></div>

  <h2>Nearby Bluetooth Devices <button class="scan" id="bt-scan">Scan (~10s)</button></h2>
  <div class="list" id="bt-nearby-list"><div class="empty">Tap Scan to look for new devices.</div></div>

  <div class="status" id="status"></div>

  <div id="kbd-overlay" class="hidden">
    <div class="kbd-box">
      <div class="kbd-title" id="kbd-title">Password</div>
      <div class="kbd-field" id="kbd-field"></div>
      <div class="kbd-rows" id="kbd-rows"></div>
    </div>
  </div>

<script>
let focusables = [];
let idx = 0;
let pendingSsid = null;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}
function setStatus(msg) {
  const s = document.getElementById("status");
  s.textContent = msg;
  if (msg) setTimeout(() => { if (s.textContent === msg) s.textContent = ""; }, 2500);
}
function rebuildFocus() {
  const overlayOpen = !document.getElementById("kbd-overlay").classList.contains("hidden");
  const scope = overlayOpen ? document.getElementById("kbd-overlay") : document.body;
  focusables = Array.from(scope.querySelectorAll("button"));
  idx = Math.max(0, Math.min(idx, focusables.length - 1));
  if (focusables[idx]) focusables[idx].focus();
}

// ---------------- On-screen keyboard ----------------
const KBD_ROWS_LOWER = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"];
let kbdShift = false;
function openKeyboard(ssid) {
  pendingSsid = ssid;
  document.getElementById("kbd-title").textContent = `Password for ${ssid}`;
  document.getElementById("kbd-field").textContent = "";
  buildKeyboard();
  document.getElementById("kbd-overlay").classList.remove("hidden");
  idx = 0;
  rebuildFocus();
}
function closeKeyboard() {
  document.getElementById("kbd-overlay").classList.add("hidden");
  pendingSsid = null;
  idx = 0;
  rebuildFocus();
}
function buildKeyboard() {
  const rows = document.getElementById("kbd-rows");
  rows.innerHTML = "";
  KBD_ROWS_LOWER.forEach((chars) => {
    const r = document.createElement("div");
    r.className = "kbd-row";
    chars.split("").forEach((c) => {
      const ch = kbdShift ? c.toUpperCase() : c;
      const b = document.createElement("button");
      b.className = "kbd-key";
      b.textContent = ch;
      b.addEventListener("click", () => { appendChar(ch); });
      r.appendChild(b);
    });
    rows.appendChild(r);
  });
  const ctrl = document.createElement("div");
  ctrl.className = "kbd-row";
  const mk = (label, cls, fn) => { const b = document.createElement("button"); b.className = "kbd-key " + cls; b.textContent = label; b.addEventListener("click", fn); return b; };
  ctrl.appendChild(mk("Shift", "wide", () => { kbdShift = !kbdShift; buildKeyboard(); rebuildFocus(); }));
  ctrl.appendChild(mk("Space", "wide", () => appendChar(" ")));
  ctrl.appendChild(mk("Del", "wide", () => { const f = document.getElementById("kbd-field"); f.dataset.val = (f.dataset.val || "").slice(0, -1); f.textContent = "*".repeat((f.dataset.val || "").length); }));
  ctrl.appendChild(mk("Cancel", "wide", closeKeyboard));
  ctrl.appendChild(mk("Connect", "wide primary", submitPassword));
  rows.appendChild(ctrl);
}
function appendChar(c) {
  const f = document.getElementById("kbd-field");
  f.dataset.val = (f.dataset.val || "") + c;
  f.textContent = "*".repeat(f.dataset.val.length);
}
async function submitPassword() {
  const f = document.getElementById("kbd-field");
  const password = f.dataset.val || "";
  setStatus("Connecting...");
  const res = await fetch(`/wifi_connect?ssid=${encodeURIComponent(pendingSsid)}&password=${encodeURIComponent(password)}`, { method: "POST" });
  const j = await res.json();
  closeKeyboard();
  setStatus(j.ok ? `Connected to ${pendingSsid}.` : `Couldn't connect: ${j.error || "unknown error"}`);
  if (j.ok) refreshWifi();
}

// ---------------- Wi-Fi ----------------
async function refreshWifi() {
  const el = document.getElementById("wifi-list");
  const res = await fetch("/wifi_scan.json").then((r) => r.json());
  if (!res.ok) { el.innerHTML = `<div class="empty">${escapeHtml(res.error || "Couldn't scan.")}</div>`; rebuildFocus(); return; }
  const nets = res.networks || [];
  if (!nets.length) { el.innerHTML = '<div class="empty">No networks found.</div>'; rebuildFocus(); return; }
  el.innerHTML = "";
  nets.forEach((n) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<div><div class="name">${escapeHtml(n.ssid)}${n.secured ? " &#128274;" : ""}</div>
      <div class="meta">${n.connected ? "Connected" : n.signal + "% signal"}</div></div>`;
    const b = document.createElement("button");
    b.className = n.connected ? "" : "primary";
    b.textContent = n.connected ? "Disconnect" : "Connect";
    b.addEventListener("click", async () => {
      if (n.connected) {
        setStatus("Disconnecting...");
        const r = await fetch("/wifi_disconnect", { method: "POST" }).then((x) => x.json());
        setStatus(r.ok ? "Disconnected." : `Couldn't disconnect: ${r.error}`);
        if (r.ok) refreshWifi();
      } else if (n.secured) {
        openKeyboard(n.ssid);
      } else {
        setStatus("Connecting...");
        const r = await fetch(`/wifi_connect?ssid=${encodeURIComponent(n.ssid)}&password=`, { method: "POST" }).then((x) => x.json());
        setStatus(r.ok ? `Connected to ${n.ssid}.` : `Couldn't connect: ${r.error}`);
        if (r.ok) refreshWifi();
      }
    });
    row.appendChild(b);
    el.appendChild(row);
  });
  rebuildFocus();
}

// ---------------- Bluetooth ----------------
async function refreshBtPaired() {
  const el = document.getElementById("bt-paired-list");
  const res = await fetch("/bt_paired.json").then((r) => r.json());
  const devices = res.devices || [];
  if (!devices.length) { el.innerHTML = '<div class="empty">No paired devices yet.</div>'; rebuildFocus(); return; }
  el.innerHTML = "";
  devices.forEach((d) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<div><div class="name">${escapeHtml(d.name)}</div>
      <div class="meta">${d.connected ? "Connected" : "Paired, not connected"}</div></div>`;
    const b = document.createElement("button");
    b.textContent = d.connected ? "Disconnect" : "Connect";
    b.addEventListener("click", async () => {
      setStatus("Working...");
      const r = await fetch(`/bt_set_enabled?id=${encodeURIComponent(d.id)}&enabled=${d.connected ? "0" : "1"}`, { method: "POST" }).then((x) => x.json());
      setStatus(r.ok ? "Done." : `Couldn't complete: ${r.error}`);
      if (r.ok) refreshBtPaired();
    });
    row.appendChild(b);
    el.appendChild(row);
  });
  rebuildFocus();
}

async function scanBluetooth() {
  const el = document.getElementById("bt-nearby-list");
  el.innerHTML = '<div class="empty">Scanning&hellip; (a few seconds)</div>';
  const res = await fetch("/bt_scan.json").then((r) => r.json());
  if (!res.ok) { el.innerHTML = `<div class="empty">${escapeHtml(res.error || "Scan failed.")}</div>`; rebuildFocus(); return; }
  const devices = res.devices || [];
  if (!devices.length) { el.innerHTML = '<div class="empty">Nothing found. Make sure the device is in pairing mode.</div>'; rebuildFocus(); return; }
  el.innerHTML = "";
  devices.forEach((d) => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<div><div class="name">${escapeHtml(d.name)}</div><div class="meta">${d.kind === "le" ? "Bluetooth LE" : "Bluetooth"}</div></div>`;
    const b = document.createElement("button");
    b.className = "primary";
    b.textContent = "Pair";
    b.addEventListener("click", async () => {
      setStatus("Pairing... (accept any prompt on the device)");
      b.disabled = true;
      const r = await fetch(`/bt_pair?id=${encodeURIComponent(d.id)}`, { method: "POST" }).then((x) => x.json());
      b.disabled = false;
      setStatus(r.ok ? `Paired with ${d.name}.` : `Couldn't pair: ${r.error}`);
      if (r.ok) { refreshBtPaired(); scanBluetooth(); }
    });
    row.appendChild(b);
    el.appendChild(row);
  });
  rebuildFocus();
}

document.getElementById("wifi-scan").addEventListener("click", refreshWifi);
document.getElementById("bt-scan").addEventListener("click", scanBluetooth);

document.addEventListener("keydown", (e) => {
  if (!focusables.length) return;
  if (e.key === "ArrowDown" || e.key === "ArrowRight") { idx = Math.min(idx + 1, focusables.length - 1); focusables[idx].focus(); e.preventDefault(); }
  else if (e.key === "ArrowUp" || e.key === "ArrowLeft") { idx = Math.max(idx - 1, 0); focusables[idx].focus(); e.preventDefault(); }
  else if (e.key === "Escape" && !document.getElementById("kbd-overlay").classList.contains("hidden")) { closeKeyboard(); }
});

refreshWifi();
refreshBtPaired();
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _send_json(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
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
        if parsed.path == "/wifi_scan.json":
            ok, data = system_actions.wifi_scan()
            self._send_json({"ok": ok, "networks": data if ok else [], "error": None if ok else data})
            return
        if parsed.path == "/bt_paired.json":
            try:
                self._send_json({"ok": True, "devices": bluetooth_pairing.list_paired_devices(), "error": None})
            except Exception as e:
                self._send_json({"ok": False, "devices": [], "error": str(e)})
            return
        if parsed.path == "/bt_scan.json":
            self._send_json(bluetooth_pairing.scan_new_devices())
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/wifi_connect":
            ssid = qs.get("ssid", [""])[0]
            password = qs.get("password", [""])[0]
            ok, err = system_actions.wifi_connect(ssid, password)
            self._send_json({"ok": ok, "error": err})
            return
        if parsed.path == "/wifi_disconnect":
            ok, err = system_actions.wifi_disconnect()
            self._send_json({"ok": ok, "error": err})
            return
        if parsed.path == "/bt_set_enabled":
            device_id = qs.get("id", [None])[0]
            enabled = qs.get("enabled", ["0"])[0] == "1"
            if not device_id:
                self._send_json({"ok": False, "error": "No device id."})
                return
            ok, err = system_actions.bluetooth_set_enabled(device_id, enabled)
            self._send_json({"ok": ok, "error": err})
            return
        if parsed.path == "/bt_pair":
            device_id = qs.get("id", [None])[0]
            if not device_id:
                self._send_json({"ok": False, "error": "No device id."})
                return
            self._send_json(bluetooth_pairing.pair_device(device_id))
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
