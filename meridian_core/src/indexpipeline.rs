//! Native index-cache pipeline — the mtime-diff, cache load/save and
//! response assembly from `_scan_library_impl` + `_entries_to_response`.
//!
//! Because building an entry (`_build_entry`: ffmpeg/PIL/mutagen/pywin32)
//! must stay in Python, this runs as two calls:
//!
//!   1. `prepare(kind, cache_path, current)` loads the cache, partitions
//!      current files into "reusable" (unchanged: keep the cached entry) vs
//!      "stale" (changed/new), stashes the reusable half natively, and hands
//!      Python just the stale paths to build.
//!   2. `finalize(kind, new_entries)` merges reusable + freshly-built,
//!      writes the new cache, and assembles the frontend response —
//!      registering every media/thumbnail path with the native media server
//!      as it goes (the token generation `_entries_to_response` did).
//!
//! The cached entries therefore never have to become Python objects; only
//! the stale subset (usually small) crosses the boundary. Python keeps its
//! original pure-Python path as a full fallback.

use std::collections::HashMap;
use std::fs;
use std::sync::{Mutex, OnceLock};

use serde_json::{json, Map, Value};

use crate::media;

struct Prepared {
    cache_path: String,
    current: Vec<(String, f64)>,
    reusable: HashMap<String, Value>,
}

static PREPARED: OnceLock<Mutex<HashMap<String, Prepared>>> = OnceLock::new();

fn prepared_map() -> &'static Mutex<HashMap<String, Prepared>> {
    PREPARED.get_or_init(|| Mutex::new(HashMap::new()))
}

fn load_cache(cache_path: &str) -> (Map<String, Value>, Map<String, Value>) {
    let empty = || (Map::new(), Map::new());
    let text = match fs::read_to_string(cache_path) {
        Ok(t) => t,
        Err(_) => return empty(),
    };
    let v: Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return empty(),
    };
    let files = v
        .get("files")
        .and_then(|f| f.as_object())
        .cloned()
        .unwrap_or_default();
    let items = v
        .get("items")
        .and_then(|i| i.as_object())
        .cloned()
        .unwrap_or_default();
    (files, items)
}

/// Load cache, partition `current` (ordered (path, mtime) pairs) into
/// reusable vs stale, stash reusable, and return the stale paths.
pub fn prepare(kind: &str, cache_path: &str, current: Vec<(String, f64)>) -> Vec<String> {
    let (cached_mtimes, cached_items) = load_cache(cache_path);

    let mut reusable: HashMap<String, Value> = HashMap::new();
    let mut stale: Vec<String> = Vec::new();

    for (path, mtime) in &current {
        let unchanged = cached_items.contains_key(path)
            && cached_mtimes
                .get(path)
                .and_then(|m| m.as_f64())
                .map(|m| m == *mtime)
                .unwrap_or(false);
        if unchanged {
            reusable.insert(path.clone(), cached_items.get(path).unwrap().clone());
        } else {
            stale.push(path.clone());
        }
    }

    let prep = Prepared {
        cache_path: cache_path.to_string(),
        current,
        reusable,
    };
    if let Ok(mut map) = prepared_map().lock() {
        map.insert(kind.to_string(), prep);
    }
    stale
}

fn media_url(token: &str) -> Value {
    Value::String(format!("http://127.0.0.1:{}/media?t={}", media::port(), token))
}

/// Merge reusable + freshly-built entries, save the cache, and build the
/// sorted frontend response (registering media tokens along the way).
/// `new_entries_json` is a JSON object {path: entry} for the stale paths.
/// Returns the response JSON array, or None if there's no prepared state for
/// `kind` (caller falls back to Python).
pub fn finalize(kind: &str, new_entries_json: &str) -> Option<String> {
    let prep = prepared_map().lock().ok()?.remove(kind)?;

    let new_entries: Map<String, Value> = serde_json::from_str(new_entries_json).ok()?;

    // Assemble fresh_items in scan order; also build the files/items maps for
    // the on-disk cache.
    let mut files = Map::new();
    let mut items_map = Map::new();
    let mut ordered: Vec<(String, Value)> = Vec::with_capacity(prep.current.len());
    for (path, mtime) in &prep.current {
        files.insert(path.clone(), json!(mtime));
        let item = prep
            .reusable
            .get(path)
            .cloned()
            .or_else(|| new_entries.get(path).cloned());
        if let Some(item) = item {
            items_map.insert(path.clone(), item.clone());
            ordered.push((path.clone(), item));
        }
    }

    // Persist {files, items}. Best-effort, exactly like _save_index_cache.
    let mut cache = Map::new();
    cache.insert("files".into(), Value::Object(files));
    cache.insert("items".into(), Value::Object(items_map));
    let _ = fs::write(&prep.cache_path, Value::Object(cache).to_string());

    // Build the response, mirroring _entries_to_response.
    let mtimes: HashMap<&String, f64> = prep.current.iter().map(|(p, m)| (p, *m)).collect();
    let mut out: Vec<Value> = Vec::with_capacity(ordered.len());
    for (path, entry) in &ordered {
        let mut e = match entry.as_object() {
            Some(o) => o.clone(),
            None => continue,
        };
        let thumb = e.remove("_thumb_path");
        let thumb_url = match thumb {
            Some(Value::String(t)) if !t.is_empty() => media_url(&media::register(&t)),
            _ => Value::Null,
        };
        e.insert("thumbUrl".into(), thumb_url);
        let file_url = media_url(&media::register(path));
        if kind == "photos" {
            e.insert("fullUrl".into(), file_url);
        } else {
            e.insert("url".into(), file_url);
        }
        if let Some(m) = mtimes.get(path) {
            e.insert("mtime".into(), json!(m));
        }
        out.push(Value::Object(e));
    }

    // Sort by (title or name).lower(), matching the Python sort key.
    out.sort_by(|a, b| sort_key(a).cmp(&sort_key(b)));

    Some(Value::Array(out).to_string())
}

fn sort_key(e: &Value) -> String {
    let o = match e.as_object() {
        Some(o) => o,
        None => return String::new(),
    };
    let s = if let Some(t) = o.get("title") {
        t.as_str().unwrap_or("")
    } else {
        o.get("name").and_then(|n| n.as_str()).unwrap_or("")
    };
    s.to_lowercase()
}

/// Discard any stashed prepare() state for `kind` (used if Python decides to
/// bail to its fallback after a successful prepare()).
pub fn discard(kind: &str) {
    if let Ok(mut map) = prepared_map().lock() {
        map.remove(kind);
    }
}
