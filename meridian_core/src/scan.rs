//! Filesystem scanning — the hot path for large media libraries. Mirrors
//! `scan_dir`, `_scan_flat`, `_list_subfolders` and the mtime-collection
//! loop inside `_scan_library_impl` from the launcher's main.py.

use std::collections::HashSet;
use std::fs;
use std::time::UNIX_EPOCH;
use walkdir::WalkDir;

use crate::pathutil::suffix_lower;

/// Build a fast lookup set of lowercase extensions (e.g. ".mp3").
fn extset(exts: &[String]) -> HashSet<String> {
    exts.iter().map(|e| e.to_lowercase()).collect()
}

/// Recursive: every file under `folder` whose lowercase suffix is in `exts`.
/// Equivalent to `scan_dir(folder, extset)` (os.walk based).
pub fn scan_dir(folder: &str, exts: &[String]) -> Vec<String> {
    let set = extset(exts);
    let mut found = Vec::new();
    for entry in WalkDir::new(folder)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        if entry.file_type().is_file() {
            let name = entry.file_name().to_string_lossy();
            if set.contains(&suffix_lower(&name)) {
                found.push(entry.path().to_string_lossy().into_owned());
            }
        }
    }
    found
}

/// Non-recursive: files directly inside `folder`. `exts = None` (empty option)
/// means no extension filter at all (Explorer section). Mirrors `_scan_flat`.
pub fn scan_flat(folder: &str, exts: Option<&[String]>) -> Vec<String> {
    let set = exts.map(extset);
    let mut found = Vec::new();
    let rd = match fs::read_dir(folder) {
        Ok(rd) => rd,
        Err(_) => return found,
    };
    for entry in rd.flatten() {
        // A single un-stat-able entry (broken reparse point, permissions)
        // is skipped, not fatal — same as the Python OSError guard.
        match entry.file_type() {
            Ok(ft) if ft.is_file() => {
                let matches = match &set {
                    None => true,
                    Some(s) => {
                        let name = entry.file_name().to_string_lossy().into_owned();
                        s.contains(&suffix_lower(&name))
                    }
                };
                if matches {
                    found.push(entry.path().to_string_lossy().into_owned());
                }
            }
            _ => continue,
        }
    }
    found
}

/// Immediate subfolder NAMES (not full paths), sorted case-insensitively.
/// Mirrors `_list_subfolders`.
pub fn list_subfolders(folder: &str) -> Vec<String> {
    let mut subs = Vec::new();
    if let Ok(rd) = fs::read_dir(folder) {
        for entry in rd.flatten() {
            if let Ok(ft) = entry.file_type() {
                if ft.is_dir() {
                    subs.push(entry.file_name().to_string_lossy().into_owned());
                }
            }
        }
    }
    subs.sort_by_key(|s| s.to_lowercase());
    subs
}

/// The `current_mtimes` build from `_scan_library_impl`: for each folder that
/// exists, recursively find matching files and pair each with its mtime.
/// Files whose mtime can't be read are skipped (Python's OSError continue).
/// Returns (path, mtime_seconds) pairs.
pub fn scan_with_mtimes(folders: &[String], exts: &[String]) -> Vec<(String, f64)> {
    let mut out = Vec::new();
    for folder in folders {
        let is_dir = fs::metadata(folder).map(|m| m.is_dir()).unwrap_or(false);
        if !is_dir {
            continue;
        }
        for path in scan_dir(folder, exts) {
            match fs::metadata(&path).and_then(|m| m.modified()) {
                Ok(mt) => {
                    if let Ok(dur) = mt.duration_since(UNIX_EPOCH) {
                        out.push((path, dur.as_secs_f64()));
                    }
                }
                Err(_) => continue,
            }
        }
    }
    out
}
