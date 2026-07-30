//! Playnite export parsing for Meridian Game Library — the read/filter/sort
//! logic from playnite_import.py. Launch actions (os.startfile / Popen) stay
//! in Python since they're Windows shell calls; this handles everything that
//! turns the raw JSON export into the entry lists the UI consumes.
//!
//! Callers pass the raw export text (already read from disk with utf-8-sig
//! by the Python shim). The None-vs-[] "is the file even there" distinction
//! is handled by the shim; these functions assume valid, present JSON.

use std::path::Path;

use serde_json::{json, Map, Value};

/// store-key -> substrings matched (case-insensitive) against Playnite Source.
fn source_aliases(key: &str) -> Option<&'static [&'static str]> {
    match key {
        "steam" => Some(&["steam"]),
        "gog" => Some(&["gog"]),
        "epic" => Some(&["epic"]),
        "amazon" => Some(&["amazon", "luna", "prime"]),
        _ => None,
    }
}

const ALL_ALIAS_GROUPS: &[&[&str]] = &[
    &["steam"],
    &["gog"],
    &["epic"],
    &["amazon", "luna", "prime"],
];

fn str_field<'a>(g: &'a Value, k: &str) -> Option<&'a str> {
    g.get(k).and_then(|v| v.as_str())
}

/// `_matches_store(source, store_key)`
fn matches_store(source: &str, store_key: &str) -> bool {
    let source = source.to_lowercase();
    if store_key == "other" {
        return !ALL_ALIAS_GROUPS
            .iter()
            .any(|grp| grp.iter().any(|alias| source.contains(alias)));
    }
    match source_aliases(store_key) {
        Some(aliases) => aliases.iter().any(|a| source.contains(a)),
        None => source.contains(&store_key.to_lowercase()),
    }
}

fn is_big_five(source: &str) -> bool {
    matches_store(source, "steam")
        || matches_store(source, "gog")
        || matches_store(source, "epic")
        || matches_store(source, "amazon")
}

/// `_entry_from_game(game)`
fn entry_from_game(g: &Value) -> Value {
    let cover = str_field(g, "CoverImagePath");
    let art = match cover {
        Some(c) if !c.is_empty() && Path::new(c).is_file() => Value::String(c.to_string()),
        _ => Value::Null,
    };
    let title = match str_field(g, "Name") {
        Some(n) if !n.is_empty() => n.to_string(),
        _ => "Untitled".to_string(),
    };
    let installed = g
        .get("IsInstalled")
        .map(|v| v.as_bool().unwrap_or(false))
        .unwrap_or(false);
    // int((Playtime or 0) / 60) — Playtime is seconds; truncate toward zero.
    let playtime_secs = g.get("Playtime").and_then(|v| v.as_i64()).unwrap_or(0);
    let playtime_minutes = playtime_secs / 60;
    let last_activity = g.get("LastActivity").cloned().unwrap_or(Value::Null);

    let mut m = Map::new();
    m.insert("id".into(), g.get("Id").cloned().unwrap_or(Value::Null));
    m.insert("title".into(), Value::String(title));
    m.insert("installed".into(), Value::Bool(installed));
    m.insert("art".into(), art);
    m.insert("playtime_minutes".into(), json!(playtime_minutes));
    m.insert("last_activity".into(), last_activity);
    Value::Object(m)
}

fn as_array(raw: &Value) -> Vec<Value> {
    raw.as_array().cloned().unwrap_or_default()
}

/// `get_recently_played` — LastActivity present, most-recent first, capped.
pub fn recently_played(raw: &Value, limit: usize) -> Value {
    let mut played: Vec<Value> = as_array(raw)
        .into_iter()
        .filter(|g| {
            g.get("LastActivity")
                .map(|v| !v.is_null() && v.as_str().map(|s| !s.is_empty()).unwrap_or(true))
                .unwrap_or(false)
        })
        .collect();
    // Stable sort by LastActivity string, reverse (ISO timestamps sort lexically).
    played.sort_by(|a, b| {
        let sa = a.get("LastActivity").and_then(|v| v.as_str()).unwrap_or("");
        let sb = b.get("LastActivity").and_then(|v| v.as_str()).unwrap_or("");
        sb.cmp(sa)
    });
    let entries: Vec<Value> = played.iter().take(limit).map(entry_from_game).collect();
    Value::Array(entries)
}

/// `get_library(store_key, ...)` — entries for one section, installed-first.
pub fn library(raw: &Value, store_key: &str) -> Value {
    let mut entries: Vec<Value> = as_array(raw)
        .iter()
        .filter(|g| matches_store(str_field(g, "Source").unwrap_or(""), store_key))
        .map(entry_from_game)
        .collect();
    entries.sort_by(|a, b| {
        // key = (not installed, title.lower()): installed games first.
        let ai = a.get("installed").and_then(|v| v.as_bool()).unwrap_or(false);
        let bi = b.get("installed").and_then(|v| v.as_bool()).unwrap_or(false);
        (!ai)
            .cmp(&(!bi))
            .then_with(|| title_lower(a).cmp(&title_lower(b)))
    });
    Value::Array(entries)
}

fn title_lower(e: &Value) -> String {
    e.get("title")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase()
}

/// `_platform_slug(raw_platform)` -> (slug, display name)
fn platform_slug(raw_platform: Option<&str>) -> (String, String) {
    let name = raw_platform.unwrap_or("").trim();
    let name = if name.is_empty() { "Unspecified" } else { name };
    let slug: String = name
        .to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { '_' })
        .collect();
    let slug = slug.trim_matches('_').to_string();
    let slug = if slug.is_empty() {
        "unspecified".to_string()
    } else {
        slug
    };
    (slug, name.to_string())
}

/// `get_other_sources` — distinct non-big-5 platforms with counts.
pub fn other_sources(raw: &Value) -> Value {
    // Preserve first-seen name; count occurrences; then sort by name.lower().
    let mut order: Vec<String> = Vec::new();
    let mut buckets: std::collections::HashMap<String, (String, i64)> =
        std::collections::HashMap::new();
    for g in as_array(raw) {
        if is_big_five(str_field(&g, "Source").unwrap_or("")) {
            continue;
        }
        let (slug, name) = platform_slug(str_field(&g, "Platform"));
        let entry = buckets.entry(slug.clone()).or_insert_with(|| {
            order.push(slug.clone());
            (name, 0)
        });
        entry.1 += 1;
    }
    let mut out: Vec<Value> = order
        .iter()
        .map(|slug| {
            let (name, count) = &buckets[slug];
            json!({"id": slug, "name": name, "count": count})
        })
        .collect();
    out.sort_by(|a, b| {
        let na = a.get("name").and_then(|v| v.as_str()).unwrap_or("").to_lowercase();
        let nb = b.get("name").and_then(|v| v.as_str()).unwrap_or("").to_lowercase();
        na.cmp(&nb)
    });
    Value::Array(out)
}

/// `get_other_source_library(source_id, ...)`
pub fn other_source_library(raw: &Value, source_id: &str) -> Value {
    let out: Vec<Value> = as_array(raw)
        .iter()
        .filter(|g| !is_big_five(str_field(g, "Source").unwrap_or("")))
        .filter(|g| platform_slug(str_field(g, "Platform")).0 == source_id)
        .map(entry_from_game)
        .collect();
    Value::Array(out)
}

/// `export_summary` — per-store counts + total.
pub fn export_summary(raw: &Value) -> Value {
    let keys = ["steam", "gog", "epic", "amazon"];
    let mut counts: Map<String, Value> = Map::new();
    for k in keys {
        counts.insert(k.to_string(), json!(0));
    }
    counts.insert("other".to_string(), json!(0));
    let arr = as_array(raw);
    for g in &arr {
        let source = str_field(g, "Source").unwrap_or("").to_lowercase();
        let mut matched = false;
        for k in keys {
            let aliases = source_aliases(k).unwrap();
            if aliases.iter().any(|a| source.contains(a)) {
                let c = counts[k].as_i64().unwrap_or(0) + 1;
                counts.insert(k.to_string(), json!(c));
                matched = true;
                break;
            }
        }
        if !matched {
            let c = counts["other"].as_i64().unwrap_or(0) + 1;
            counts.insert("other".to_string(), json!(c));
        }
    }
    counts.insert("total".to_string(), json!(arr.len()));
    Value::Object(counts)
}
