# meridian_core — native Rust backend

Shared native backend for **Meridian Launcher** and **Meridian Game Library**.
It moves the portable, hot-path backend logic out of Python and into a compiled
Rust extension module (`meridian_core.pyd` on Windows), while everything that
genuinely needs Python/Windows stays in Python and calls into it.

The frontend (the `frontend/` HTML/CSS/JS and the pywebview `Api` bridge) is
**unchanged** — every function that now delegates to Rust keeps the exact same
name and signature, so the JS side and the `Api` contract are untouched.

## What moved to Rust

| Area | Rust function(s) | Was (Python) |
|------|------------------|--------------|
| Recursive library scan + ext filter | `scan_dir`, `scan_with_mtimes` | `scan_dir`, the mtime loop in `_scan_library_impl` |
| Single-folder listing | `scan_flat`, `list_subfolders` | `_scan_flat`, `_list_subfolders` |
| Media-server tokens / thumb cache keys | `sha1_hex` | `token_for`, `_cache_path` |
| Duration + category icon | `fmt_duration`, `generic_icon_keyword` | `fmt_duration`, `_generic_icon_keyword_for` |
| Settings merge / migration | `deep_merge_json`, `migrate_theme_media_json` | `_deep_merge`, `_migrate_theme_media` (both apps) |
| Name helpers | `slugify`, `display_name` | `slugify`, `display_name` (both apps) |
| Media file server (`/media` + HTTP Range) | `media_start`, `media_register`, `media_port` | the `/media` route of `MediaHandler` + `token_for`/`TOKEN_MAP` |
| Library index cache diff + response assembly | `index_prepare`, `index_finalize`, `index_discard` | the mtime-diff, cache load/save and `_entries_to_response` in `_scan_library_impl` |
| Playnite export parsing | `playnite_recently_played`, `playnite_library`, `playnite_other_sources`, `playnite_other_source_library`, `playnite_export_summary` | the read/filter/sort half of `playnite_import.py` |

The heavy filesystem walk for a large media library — the recursive scan plus
per-file `mtime` read that `_scan_library_impl` does on every cold scan — is now
a single native call (`scan_with_mtimes`).

### Media server (two-server design)

The old `MediaHandler` did two unrelated jobs on one port: serve media files
(`/media?t=<token>`) and run three `evaluate_js`-coupled control routes
(`/internal/open-explorer`, `/internal/open-browser`, `/internal/plugin-exited`).
Only the first is portable, so it split cleanly:

- The **native `tiny_http` server** (started by `media_start()`) serves `/media`
  with full HTTP Range support, from a Rust worker pool. It owns the token→path
  map that `TOKEN_MAP` used to. `media_url()` in main.py points at it and calls
  `media_register()` when the native server is up.
- The **Python server stays up** for the `/internal/*` routes (they call
  `webview.evaluate_js`, which must be Python) and as a media fallback. Children
  still read `internal_port.txt` (the Python port) exactly as before — untouched.

### Index-cache pipeline

`_scan_library_impl` now runs its diff natively in two calls, because building an
entry (`_build_entry`: ffmpeg/PIL/mutagen/pywin32) must stay Python:

1. `index_prepare(kind, cache_path, current)` — Rust loads the cache, partitions
   current files into unchanged (keep cached entry) vs stale, stashes the
   unchanged half natively, and returns just the stale paths.
2. Python builds *only* the stale entries with `_build_entry`.
3. `index_finalize(kind, new_entries)` — Rust merges, writes the new cache, and
   assembles the sorted frontend response, registering each media/thumbnail path
   with the native media server as it goes (the token generation
   `_entries_to_response` did).

So the cached entries never become Python objects; only the (usually small)
stale subset crosses the boundary. This is what makes the diff worth porting —
and it's why it's coupled to the media server (the tokens it registers must be
servable). If the native media server isn't up, or anything fails, main.py falls
back to the identical pure-Python path.

## What deliberately stayed in Python

These need Python libraries, Windows COM/APIs, or the GUI, so porting them would
mean *more* interop cost for no real gain (or simply isn't possible in Rust):

- **pywebview** and the whole `Api` bridge / window lifecycle.
- **Thumbnails & tags**: `get_video_thumb`/`read_video_meta` (ffmpeg/ffprobe),
  `get_music_thumb`/`read_audio_meta` (mutagen), `get_photo_thumb` (Pillow),
  `get_file_icon` (pywin32 COM icon extraction).
- **The media HTTP server** (tightly coupled to pywebview `evaluate_js`
  callbacks).
- **Controller stack** (`gameinput_api.py`, `controller_input.py`, the GameInput
  ctypes vtable work), `system_actions.py`, the plug-on servers.
- **Playnite launch actions** (`launch_game`, `show_in_playnite`,
  `get_play_action_exe_*`) — these are `os.startfile` / `subprocess.Popen`
  Windows shell calls; only the *parsing* moved.
- `default_settings()` stays in Python: it's declarative data, kept as one
  readable source of truth. Only the algorithms that transform it moved.

## Fallback design (best-effort)

Every delegating function is wrapped like this:

```python
try:
    import meridian_core as _mc
except Exception:
    _mc = None

def scan_dir(folder, extset):
    if _mc is not None:
        try:
            return _mc.scan_dir(str(folder), list(extset))
        except Exception:
            pass
    # ... original pure-Python implementation (unchanged) ...
```

So the apps run **identically** whether or not the native module is present — a
source checkout that hasn't been built yet, or a machine without Rust, just uses
the original Python. This matches the suite's "prefer non-fatal / best-effort for
optional components" convention.

## Building

`BuildMeridianCore.bat` (repo root) does everything: it runs
`cargo build --release`, renames the resulting `meridian_core.dll` to
`meridian_core.pyd`, and stages a copy next to both `main.py` (Launcher) and
`Meridian Game Library/main.py`. The app build scripts
(`buildMeridianLauncher.bat`, `Meridian Game Library/build_MeridianGameLibrary.bat`,
and the `CompileAndPackage.bat` / `quickcompile.bat` orchestrators) call it
automatically and then bundle the `.pyd` via PyInstaller.

Requirements: the **Rust toolchain** (install once from <https://rustup.rs>) plus
the MSVC C++ Build Tools you already use for `gameinput_native` (Rust uses the
same linker on Windows). PyO3 builds the extension against whatever `python` is
on PATH, so build the core with the same interpreter you use for PyInstaller.

Manually, if you prefer:

```bat
cd meridian_core
set PYO3_PYTHON=C:\path\to\python.exe
cargo build --release
copy target\release\meridian_core.dll ..\meridian_core.pyd
copy target\release\meridian_core.dll "..\Meridian Game Library\meridian_core.pyd"
```

## Verification status — please read

- **Logic parity is verified on Linux.** `parity_test.py` runs every native
  function against a faithful copy of the original Python over synthetic
  filesystem trees, settings dicts and a Playnite export, and asserts equality
  (all 45+ checks pass). The Playnite functions are additionally tested through
  the real wired `playnite_import.py` with `_mc` on vs. forced off, confirming
  native and fallback agree in situ. `media_index_test.py` starts the native
  media server and hits it over real HTTP (full GET, `Range` GET, open-ended
  range, bad-token/non-media 404s), and checks the index pipeline
  (`prepare`/`finalize`) produces byte-identical responses and cache files to a
  Python reference of `_scan_library_impl` + `_entries_to_response`.
- **Not yet tested on Windows hardware.** I could not produce or run the Windows
  `.pyd` in this environment, so the MSVC build, the PyInstaller bundling, and
  behavior on real Windows paths (backslashes, drive roots, UNC) still need a
  test build on your machine. The path helpers are written to match Windows
  `pathlib` (splitting on both `/` and `\`), but that specific behavior is the
  main thing to sanity-check on-device. The media server is verified at the HTTP
  level on Linux, but streaming to the actual WebView2 (video seeking, large
  files) is worth a real-hardware pass too.
- **One known non-issue:** the cold-scan `mtime` float from Rust
  (`SystemTime` → `as_secs_f64`) and Python's `os.path.getmtime` both derive
  from the same `st_mtime`. If they ever differ in the last float bit, the worst
  case is one entry being rebuilt once and then re-cached — self-healing, never
  incorrect output.

To run the parity harness after building (on any platform):

```bash
cd meridian_core && cargo build --release
cp target/release/libmeridian_core.so ./meridian_core.so   # Windows: .dll -> meridian_core.pyd
python3 parity_test.py
```
