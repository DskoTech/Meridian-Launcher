"""task_manager_server.py — "Task Manager" plug-on (System section).

An in-app equivalent of Windows' Task Manager: every open, taskbar-
visible window with live CPU%/RAM, focus/close actions - without
alt-tabbing out to the real one. Runs as an "addon" plug-on (see
plugin_manager.py) boxed into NetBrowse the same way the other System
plug-ons work, so it's reachable and closeable exactly like any other
System section entry.

Loopback-only (127.0.0.1) - unlike phone_type_server.py this has no
reason to be reachable from anywhere but this machine, so it isn't.
Runs in-process and calls tasks_win.py directly (no subprocess, no
second Python interpreter) since it's already living in Meridian
Launcher's own process.

CONTROLLER-FIRST LAYOUT: this is meant to be driven entirely by a
gamepad from a couch, not a mouse. Every row is a 2-column grid (Focus /
Close) so Up/Down moves between tasks and Left/Right moves between a
row's two actions - real 2D grid navigation, not just tab order - with
a large, high-contrast focus outline sized for a TV at a distance. See
_PAGE's <style>/<script> for the actual key handling; it listens for
both ArrowUp/Down/Left/Right AND Tab-order-safe fallbacks, since which
one a boxed page receives depends on how the embedding browser forwards
controller input.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import tasks_win

IS_WINDOWS = sys.platform == "win32"

# Fixed rather than OS-assigned, same reasoning as phone_type_server.py's
# DEFAULT_PORT: a static plugin.json can't know a randomly-chosen port
# ahead of time. Different port than phone_type_server so both plug-ons
# can run at once.
DEFAULT_PORT = 58735

_state = {"httpd": None, "port": None}

_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Task Manager — Meridian Launcher</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; padding:22px; background:#0b1410; color:#eafff0; font-family:system-ui,sans-serif; }
  h1 { font-size:20px; color:#7CFFB2; margin:0 0 4px; }
  .sub { font-size:13px; color:#8aa; margin:0 0 18px; }
  #list { display:flex; flex-direction:column; gap:10px; }
  .row {
    display:grid; grid-template-columns:44px 1fr auto auto; align-items:center; gap:14px;
    background:#111f18; border:1px solid #1e3327; border-radius:12px; padding:10px 14px;
  }
  .row img { width:32px; height:32px; border-radius:6px; }
  .row .ph { width:32px; height:32px; border-radius:6px; background:#1e3327; display:flex;
    align-items:center; justify-content:center; font-weight:700; color:#7CFFB2; }
  .info { min-width:0; }
  .title { font-size:15px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .meta { font-size:12px; color:#8aa; font-family:monospace; margin-top:2px; }
  .meta .high { color:#ff6b5b; }
  .meta .med { color:#facc15; }
  .row button {
    font-size:14px; font-weight:600; padding:10px 18px; border-radius:8px; border:2px solid transparent;
    background:#17281f; color:#eafff0; cursor:pointer;
  }
  .row button.danger { color:#ff8a7a; }
  .row button:focus-visible {
    outline:none; border-color:#7CFFB2; box-shadow:0 0 0 3px rgba(124,255,178,0.35);
  }
  .empty { color:#8aa; font-size:14px; padding:30px 0; text-align:center; }
</style></head>
<body>
  <h1>Task Manager</h1>
  <p class="sub">Sorted by CPU. Up/Down between apps, Left/Right between Focus/Close, A/Enter to activate.</p>
  <div id="list"><div class="empty">Loading&hellip;</div></div>
<script>
let tasks = [];
let row = 0;   // selected task row
let col = 0;   // 0 = Focus, 1 = Close

function fmtMb(mb) { return mb >= 1024 ? (mb/1024).toFixed(1) + " GB" : Math.round(mb) + " MB"; }

function render() {
  const list = document.getElementById("list");
  if (!tasks.length) { list.innerHTML = '<div class="empty">Nothing open right now.</div>'; return; }
  list.innerHTML = "";
  tasks.forEach((t, i) => {
    const r = document.createElement("div");
    r.className = "row";
    const icon = t.icon
      ? `<img src="${t.icon}" alt="">`
      : `<div class="ph">${(t.title || "?").charAt(0).toUpperCase()}</div>`;
    const res = t.resources || { cpu_percent: null, mem_mb: null };
    const cpuClass = res.cpu_percent >= 50 ? "high" : res.cpu_percent >= 20 ? "med" : "";
    const cpuText = res.cpu_percent != null ? res.cpu_percent.toFixed(1) + "% CPU" : "? CPU";
    const memText = res.mem_mb != null ? fmtMb(res.mem_mb) + " RAM" : "? RAM";
    r.innerHTML = `${icon}
      <div class="info">
        <div class="title">${escapeHtml(t.title || "(untitled)")}</div>
        <div class="meta"><span class="${cpuClass}">${cpuText}</span> &middot; ${memText}</div>
      </div>
      <button data-act="focus" data-i="${i}">Focus</button>
      <button data-act="close" data-i="${i}" class="danger">Close</button>`;
    list.appendChild(r);
  });
  applyFocus();
  list.querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => act(b.dataset.act, parseInt(b.dataset.i, 10)));
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}

function applyFocus() {
  if (!tasks.length) return;
  row = Math.max(0, Math.min(row, tasks.length - 1));
  const rows = document.querySelectorAll(".row");
  const btns = rows[row] ? rows[row].querySelectorAll("button") : null;
  if (btns && btns[col]) btns[col].focus();
}

async function act(action, i) {
  const t = tasks[i];
  if (!t) return;
  await fetch(`/${action}?id=${t.id}`, { method: "POST" });
  if (action === "close") setTimeout(refresh, 400);
}

async function refresh() {
  try {
    const res = await fetch("/tasks.json");
    tasks = await res.json();
    tasks.sort((a, b) => (b.resources ? b.resources.cpu_percent : 0) - (a.resources ? a.resources.cpu_percent : 0));
  } catch (e) { tasks = []; }
  render();
}

document.addEventListener("keydown", (e) => {
  if (!tasks.length) return;
  if (e.key === "ArrowDown") { row = Math.min(row + 1, tasks.length - 1); applyFocus(); e.preventDefault(); }
  else if (e.key === "ArrowUp") { row = Math.max(row - 1, 0); applyFocus(); e.preventDefault(); }
  else if (e.key === "ArrowRight") { col = 1; applyFocus(); e.preventDefault(); }
  else if (e.key === "ArrowLeft") { col = 0; applyFocus(); e.preventDefault(); }
});

refresh();
setInterval(refresh, 2000);
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def _send(self, data, content_type, code=200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/tasks.json":
            try:
                tasks = tasks_win.list_open_tasks()
            except Exception:
                tasks = []
            self._send(json.dumps(tasks).encode("utf-8"), "application/json")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        hwnd = qs.get("id", [None])[0]
        if parsed.path == "/focus" and hwnd:
            ok = tasks_win.focus_task(hwnd)
            self._send(json.dumps({"ok": ok}).encode("utf-8"), "application/json")
            return
        if parsed.path == "/close" and hwnd:
            ok = tasks_win.close_task(hwnd)
            self._send(json.dumps({"ok": ok}).encode("utf-8"), "application/json")
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
