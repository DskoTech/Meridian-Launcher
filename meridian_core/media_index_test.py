"""
Exercises the native media server (real HTTP, full + Range) and the index
pipeline (prepare/finalize) against a Python reference of the original
_scan_library_impl + _entries_to_response logic.
"""
import json, os, tempfile, urllib.request, hashlib
import meridian_core as mc

FAILS = []
def check(name, a, b):
    if a != b:
        FAILS.append(name); print(f"  MISMATCH {name}\n   a={a!r}\n   b={b!r}")
    else:
        print(f"  ok  {name}")

# ---------------- media server ----------------
print("== media server ==")
port = mc.media_start()
assert port and port == mc.media_port(), (port, mc.media_port())
print("  server on port", port)

with tempfile.TemporaryDirectory() as td:
    blob = bytes(range(256)) * 40  # 10240 bytes
    fp = os.path.join(td, "clip.bin"); open(fp, "wb").write(blob)
    tok = mc.media_register(fp)
    check("token==sha1", tok, hashlib.sha1(fp.encode()).hexdigest())

    url = f"http://127.0.0.1:{port}/media?t={tok}"
    # full GET
    with urllib.request.urlopen(url) as r:
        body = r.read()
        check("full status", r.status, 200)
        check("full length", len(body), len(blob))
        check("full bytes", body, blob)
        check("accept-ranges", r.headers.get("Accept-Ranges"), "bytes")
    # range GET
    req = urllib.request.Request(url, headers={"Range": "bytes=100-199"})
    with urllib.request.urlopen(req) as r:
        body = r.read()
        check("range status", r.status, 206)
        check("range length", len(body), 100)
        check("range bytes", body, blob[100:200])
        check("content-range", r.headers.get("Content-Range"), f"bytes 100-199/{len(blob)}")
    # open-ended range
    req = urllib.request.Request(url, headers={"Range": "bytes=10200-"})
    with urllib.request.urlopen(req) as r:
        body = r.read()
        check("openrange length", len(body), len(blob) - 10200)
        check("openrange bytes", body, blob[10200:])
    # bad token -> 404
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/media?t=deadbeef")
        check("bad token 404", "no-error", "404")
    except urllib.error.HTTPError as e:
        check("bad token 404", e.code, 404)
    # non-media path -> 404
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/internal/x")
        check("non-media 404", "no-error", "404")
    except urllib.error.HTTPError as e:
        check("non-media 404", e.code, 404)

# ---------------- index pipeline ----------------
print("== index pipeline ==")
def py_media_url(x):
    return f"http://127.0.0.1:{mc.media_port()}/media?t={hashlib.sha1(str(x).encode()).hexdigest()}" if x else None

def py_reference(kind, cache_path, current, new_entries):
    # load
    cache = {"files": {}, "items": {}}
    if os.path.exists(cache_path):
        try: cache = json.loads(open(cache_path, encoding="utf-8").read())
        except Exception: pass
    cached_m, cached_i = cache.get("files", {}), cache.get("items", {})
    fresh = {}
    for path, mtime in current.items():
        if path in cached_i and cached_m.get(path) == mtime:
            fresh[path] = cached_i[path]
        else:
            fresh[path] = new_entries[path]
    # response
    items = []
    for path, entry in fresh.items():
        e = dict(entry); thumb = e.pop("_thumb_path", None)
        e["thumbUrl"] = py_media_url(thumb) if thumb else None
        if kind == "photos": e["fullUrl"] = py_media_url(path)
        else: e["url"] = py_media_url(path)
        if path in current: e["mtime"] = current[path]
        items.append(e)
    items.sort(key=lambda e: e.get("title", e["name"]).lower())
    return items, {"files": current, "items": fresh}

with tempfile.TemporaryDirectory() as td:
    cache_path = os.path.join(td, "index_music.json")
    # pre-existing cache: song A unchanged, song B stale (mtime changed)
    open(cache_path, "w").write(json.dumps({
        "files": {"/m/a.mp3": 100.0, "/m/b.mp3": 200.0},
        "items": {
            "/m/a.mp3": {"name": "a.mp3", "title": "Alpha", "_thumb_path": "/c/a.jpg", "artist": "X"},
            "/m/b.mp3": {"name": "b.mp3", "title": "OLD B", "_thumb_path": "/c/bold.jpg"},
        },
    }))
    current = {"/m/a.mp3": 100.0, "/m/b.mp3": 250.0, "/m/c.mp3": 300.0}  # a unchanged, b changed, c new

    stale = mc.index_prepare("music", cache_path, list(current.items()))
    check("stale set", sorted(stale), sorted(["/m/b.mp3", "/m/c.mp3"]))

    # Python "builds" the stale entries
    new_entries = {
        "/m/b.mp3": {"name": "b.mp3", "title": "Beta", "_thumb_path": "/c/bnew.jpg"},
        "/m/c.mp3": {"name": "c.mp3", "title": "Gamma", "_thumb_path": ""},  # empty thumb -> null
    }
    rust_resp = json.loads(mc.index_finalize("music", json.dumps(new_entries)))
    ref_resp, ref_cache = py_reference("music", cache_path, current, new_entries)
    check("response parity", rust_resp, ref_resp)

    # saved cache matches reference
    saved = json.loads(open(cache_path, encoding="utf-8").read())
    check("saved files", saved["files"], ref_cache["files"])
    check("saved items", saved["items"], ref_cache["items"])

    # thumbUrl null for empty thumb (Gamma)
    gamma = [e for e in rust_resp if e["title"] == "Gamma"][0]
    check("empty thumb -> null", gamma["thumbUrl"], None)
    # reused entry kept its cached data (artist X on Alpha)
    alpha = [e for e in rust_resp if e["title"] == "Alpha"][0]
    check("reused cached fields", alpha.get("artist"), "X")

    # photos kind uses fullUrl
    cp2 = os.path.join(td, "index_photos.json")
    cur2 = {"/p/x.jpg": 1.0}
    mc.index_prepare("photos", cp2, list(cur2.items()))
    ne2 = {"/p/x.jpg": {"name": "x.jpg", "title": "Pic", "_thumb_path": "/c/x.jpg"}}
    r2 = json.loads(mc.index_finalize("photos", json.dumps(ne2)))
    check("photos uses fullUrl", "fullUrl" in r2[0] and "url" not in r2[0], True)

    # finalize with no prepared state -> None (caller falls back)
    check("finalize no-state -> None", mc.index_finalize("nonexistent", "{}"), None)

print()
if FAILS:
    print(f"*** {len(FAILS)} FAIL(S) ***"); raise SystemExit(1)
print("ALL MEDIA + INDEX CHECKS PASSED")
