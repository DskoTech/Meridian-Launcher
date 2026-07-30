"""
Parity harness: meridian_core (Rust) vs the original Python implementations.

Each Python function below is a faithful copy of the original from main.py /
store.py / playnite_import.py (same logic, deps stripped). We run both over
synthetic data and assert equality. Runs on Linux with forward-slash paths so
PosixPath and the Rust (Windows-compatible) splitter agree.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import meridian_core as mc

FAILS = []
def check(name, py, rs):
    if py != rs:
        FAILS.append((name, py, rs))
        print(f"  MISMATCH {name}\n    py={py!r}\n    rs={rs!r}")
    else:
        print(f"  ok  {name}")

# ---------------- original Python impls (copied) ----------------
MUSIC_EXT = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".wma", ".aac"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz"}
INSTALLER_EXT = {".exe", ".msi"}
DOC_EXT = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}

def py_scan_dir(folder, extset):
    found = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if Path(name).suffix.lower() in extset:
                found.append(str(Path(root) / name))
    return found

def py_scan_flat(folder, extset):
    found = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                try:
                    if entry.is_file() and (extset is None or Path(entry.name).suffix.lower() in extset):
                        found.append(entry.path)
                except OSError:
                    continue
    except OSError:
        pass
    return found

def py_list_subfolders(folder):
    subs = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                try:
                    if entry.is_dir():
                        subs.append(entry.name)
                except OSError:
                    continue
    except OSError:
        pass
    return sorted(subs, key=str.lower)

def py_fmt_duration(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def py_generic_icon_keyword_for(path):
    ext = Path(path).suffix.lower()
    if ext in PHOTO_EXT: return "photos"
    if ext in VIDEO_EXT: return "videos"
    if ext in MUSIC_EXT: return "music"
    if ext in ARCHIVE_EXT: return "archive"
    if ext in INSTALLER_EXT: return "apps"
    if ext in DOC_EXT: return "document"
    return "generic"

def py_sha1(s): return hashlib.sha1(s.encode("utf-8")).hexdigest()

def py_deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            py_deep_merge(base[k], v)
        else:
            base[k] = v

def py_migrate_theme_media(m):
    if m.get("background_image") and not m.get("background_by_theme"):
        m["background_by_theme"] = {"dawning_horizon": m["background_image"]}
    if m.get("overlay_image") and not m.get("overlay_by_theme"):
        m["overlay_by_theme"] = {"dawning_horizon": m["overlay_image"]}
        m["overlay_enabled_by_theme"] = {"dawning_horizon": bool(m.get("overlay_enabled"))}

def py_slugify(name):
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "section"

def py_display_name(path): return Path(path).stem

# playnite
SOURCE_ALIASES = {"steam": ["steam"], "gog": ["gog"], "epic": ["epic"], "amazon": ["amazon", "luna", "prime"]}
def py_matches_store(source, store_key):
    source = (source or "").lower()
    if store_key == "other":
        return not any(any(a in source for a in al) for al in SOURCE_ALIASES.values())
    aliases = SOURCE_ALIASES.get(store_key, [store_key])
    return any(a in source for a in aliases)
def py_entry_from_game(game):
    cover = game.get("CoverImagePath")
    return {"id": game.get("Id"), "title": game.get("Name") or "Untitled",
            "installed": bool(game.get("IsInstalled")),
            "art": cover if cover and os.path.isfile(cover) else None,
            "playtime_minutes": int((game.get("Playtime") or 0) / 60),
            "last_activity": game.get("LastActivity")}
def py_recently_played(raw, limit=5):
    played = [g for g in raw if g.get("LastActivity")]
    played.sort(key=lambda g: g.get("LastActivity"), reverse=True)
    return [py_entry_from_game(g) for g in played[:limit]]
def py_library(raw, store_key):
    entries = [py_entry_from_game(g) for g in raw if py_matches_store(g.get("Source"), store_key)]
    entries.sort(key=lambda e: (not e["installed"], e["title"].lower()))
    return entries
def py_platform_slug(raw_platform):
    name = (raw_platform or "").strip() or "Unspecified"
    slug = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")
    return slug or "unspecified", name
def py_is_big_five(source):
    return (py_matches_store(source,"steam") or py_matches_store(source,"gog") or
            py_matches_store(source,"epic") or py_matches_store(source,"amazon"))
def py_other_sources(raw):
    buckets = {}
    for game in raw:
        if py_is_big_five(game.get("Source") or ""): continue
        slug, name = py_platform_slug(game.get("Platform"))
        b = buckets.setdefault(slug, {"id": slug, "name": name, "count": 0})
        b["count"] += 1
    return sorted(buckets.values(), key=lambda b: b["name"].lower())
def py_other_source_library(raw, source_id):
    out = []
    for game in raw:
        if py_is_big_five(game.get("Source") or ""): continue
        slug, _ = py_platform_slug(game.get("Platform"))
        if slug == source_id: out.append(py_entry_from_game(game))
    return out
def py_export_summary(raw):
    counts = {k: 0 for k in SOURCE_ALIASES}; counts["other"] = 0
    for game in raw:
        source = (game.get("Source") or "").lower(); matched = False
        for key, aliases in SOURCE_ALIASES.items():
            if any(a in source for a in aliases):
                counts[key] += 1; matched = True; break
        if not matched: counts["other"] += 1
    counts["total"] = len(raw); return counts

# ---------------- run ----------------
print("== simple helpers ==")
for sec in [0, 5, 59, 60, 61, 3599, 3600, 3661, 86399, 100000]:
    check(f"fmt_duration({sec})", py_fmt_duration(sec), mc.fmt_duration(sec))
for p in ["a.MP3","x/y/z.WEBP","f.exe","g.zip","h.docx","noext","q.7z","r.tar","s.unknown",".hidden"]:
    check(f"icon_kw({p})", py_generic_icon_keyword_for(p), mc.generic_icon_keyword(p))
for s in ["C:/games/x.exe","hello world","",u"caf\u00e9/song.mp3"]:
    check(f"sha1({s!r})", py_sha1(s), mc.sha1_hex(s))
for nm in ["My Cool Section!!","  spaces  ","---","Ünïcode Wörld","a&&b__c","2024 Games"]:
    check(f"slugify({nm!r})", py_slugify(nm), mc.slugify(nm))
for p in ["C:/a/b/chrome.exe","song.title.flac",".bashrc","plain","x/y.tar.gz"]:
    check(f"display_name({p!r})", py_display_name(p), mc.display_name(p))

print("== scanning (synthetic tree) ==")
with tempfile.TemporaryDirectory() as td:
    layout = {
        "music/a.mp3": b"", "music/b.FLAC": b"", "music/cover.jpg": b"",
        "music/live/c.wav": b"", "music/live/deep/d.ogg": b"",
        "photos/p1.png": b"", "photos/p2.JPEG": b"", "photos/readme.txt": b"",
        "videos/v1.mp4": b"", "videos/v2.mkv": b"", "mixed/x.exe": b"", "mixed/y": b"",
    }
    for rel, data in layout.items():
        fp = Path(td) / rel; fp.parent.mkdir(parents=True, exist_ok=True); fp.write_bytes(data)
    music = str(Path(td)/"music")
    check("scan_dir music", sorted(py_scan_dir(music, MUSIC_EXT)), sorted(mc.scan_dir(music, list(MUSIC_EXT))))
    check("scan_flat music(photo)", sorted(py_scan_flat(music, PHOTO_EXT)), sorted(mc.scan_flat(music, list(PHOTO_EXT))))
    check("scan_flat music(all)", sorted(py_scan_flat(music, None)), sorted(mc.scan_flat(music, None)))
    check("list_subfolders music", py_list_subfolders(music), mc.list_subfolders(music))
    folders = [str(Path(td)/"music"), str(Path(td)/"photos"), str(Path(td)/"nonexistent")]
    py_mt = {p: os.path.getmtime(p) for f in folders if os.path.isdir(f) for p in py_scan_dir(f, MUSIC_EXT|PHOTO_EXT)}
    rs_mt = dict(mc.scan_with_mtimes(folders, list(MUSIC_EXT|PHOTO_EXT)))
    check("scan_with_mtimes keys", sorted(py_mt), sorted(rs_mt))

print("== settings algorithms ==")
base = {"a": 1, "nested": {"x": 1, "y": 2}, "list": [1,2]}
over = {"a": 9, "nested": {"y": 5, "z": 7}, "new": True, "list": [3]}
pyb = json.loads(json.dumps(base)); py_deep_merge(pyb, over)
rsb = json.loads(mc.deep_merge_json(json.dumps(base), json.dumps(over)))
check("deep_merge", pyb, rsb)
for m in [
    {"background_image": "bg.png", "background_by_theme": {}, "overlay_image": None},
    {"background_image": None, "background_by_theme": {}},
    {"overlay_image": "o.png", "overlay_by_theme": {}, "overlay_enabled": True},
    {"background_image": "x", "background_by_theme": {"dawning_horizon": "keep"}},
]:
    pym = json.loads(json.dumps(m)); py_migrate_theme_media(pym)
    rsm = json.loads(mc.migrate_theme_media_json(json.dumps(m)))
    check(f"migrate_theme_media {list(m)}", pym, rsm)

print("== playnite ==")
# include a real on-disk cover to exercise the isfile() art check
with tempfile.TemporaryDirectory() as td:
    real_cover = str(Path(td)/"cover.png"); Path(real_cover).write_bytes(b"x")
    raw = [
        {"Id":"1","Name":"Portal","Source":"Steam","IsInstalled":True,"Playtime":7200,"LastActivity":"2026-07-20T10:00:00Z","CoverImagePath":real_cover,"Platform":"PC"},
        {"Id":"2","Name":"Witcher","Source":"GOG","IsInstalled":False,"Playtime":0,"LastActivity":"2026-07-25T09:00:00Z","CoverImagePath":"C:/missing.png","Platform":"PC"},
        {"Id":"3","Name":None,"Source":"Epic Games","IsInstalled":True,"Playtime":125,"LastActivity":None,"Platform":"PC"},
        {"Id":"4","Name":"Zelda","Source":"Nintendo","IsInstalled":True,"Playtime":3600,"LastActivity":"2026-07-26T09:00:00Z","Platform":"Nintendo Switch"},
        {"Id":"5","Name":"Halo","Source":"Xbox","IsInstalled":False,"Playtime":600,"LastActivity":"2026-07-24T09:00:00Z","Platform":"PC"},
        {"Id":"6","Name":"Alt","Source":"amazon luna","IsInstalled":True,"Playtime":90,"LastActivity":"2026-07-23T00:00:00Z","Platform":""},
    ]
    rawj = json.dumps(raw)
    check("recently_played", py_recently_played(raw, 5), json.loads(mc.playnite_recently_played(rawj, 5)))
    for key in ["steam","gog","epic","amazon","other"]:
        check(f"library[{key}]", py_library(raw, key), json.loads(mc.playnite_library(rawj, key)))
    check("other_sources", py_other_sources(raw), json.loads(mc.playnite_other_sources(rawj)))
    check("other_src_lib[nintendo_switch]", py_other_source_library(raw,"nintendo_switch"), json.loads(mc.playnite_other_source_library(rawj,"nintendo_switch")))
    check("export_summary", py_export_summary(raw), json.loads(mc.playnite_export_summary(rawj)))

print()
if FAILS:
    print(f"*** {len(FAILS)} MISMATCH(ES) ***"); raise SystemExit(1)
print("ALL PARITY CHECKS PASSED")
