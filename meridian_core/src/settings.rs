//! The reusable *algorithms* from store.py — deep merge, theme-media
//! migration, slugify, display_name. `default_settings()` itself stays in
//! Python (declarative data; one readable source of truth), so this module
//! only ports the error-prone logic that transforms it.

use serde_json::{Map, Value};

use crate::pathutil::stem;

/// Recursive dict merge matching store.py `_deep_merge(base, override)`:
/// override wins, except when both sides are objects (then recurse).
pub fn deep_merge(base: &mut Value, override_v: &Value) {
    if let (Value::Object(base_map), Value::Object(over_map)) = (&mut *base, override_v) {
        for (k, v) in over_map {
            match (base_map.get_mut(k), v) {
                (Some(bv @ Value::Object(_)), Value::Object(_)) => deep_merge(bv, v),
                _ => {
                    base_map.insert(k.clone(), v.clone());
                }
            }
        }
    } else {
        *base = override_v.clone();
    }
}

/// Python truthiness for the values migrate_theme_media inspects:
/// null/false/0/""/[]/{} are falsy; everything else truthy.
fn truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
        Some(Value::Number(n)) => n.as_f64().map(|f| f != 0.0).unwrap_or(true),
    }
}

/// Fold legacy single background/overlay values into the per-theme dicts,
/// matching store.py `_migrate_theme_media(m)`. Mutates `m` in place.
pub fn migrate_theme_media(m: &mut Value) {
    let obj = match m.as_object_mut() {
        Some(o) => o,
        None => return,
    };

    if truthy(obj.get("background_image")) && !truthy(obj.get("background_by_theme")) {
        let img = obj.get("background_image").cloned().unwrap_or(Value::Null);
        let mut d = Map::new();
        d.insert("dawning_horizon".to_string(), img);
        obj.insert("background_by_theme".to_string(), Value::Object(d));
    }

    if truthy(obj.get("overlay_image")) && !truthy(obj.get("overlay_by_theme")) {
        let img = obj.get("overlay_image").cloned().unwrap_or(Value::Null);
        let mut d = Map::new();
        d.insert("dawning_horizon".to_string(), img);
        obj.insert("overlay_by_theme".to_string(), Value::Object(d));

        let enabled = truthy(obj.get("overlay_enabled"));
        let mut d2 = Map::new();
        d2.insert("dawning_horizon".to_string(), Value::Bool(enabled));
        obj.insert("overlay_enabled_by_theme".to_string(), Value::Object(d2));
    }
}

/// store.py `slugify(name)`.
pub fn slugify(name: &str) -> String {
    let mut slug: String = name
        .chars()
        .flat_map(|c| {
            if c.is_alphanumeric() {
                c.to_lowercase().collect::<Vec<_>>()
            } else {
                vec!['-']
            }
        })
        .collect();
    slug = slug.trim_matches('-').to_string();
    while slug.contains("--") {
        slug = slug.replace("--", "-");
    }
    if slug.is_empty() {
        "section".to_string()
    } else {
        slug
    }
}

/// store.py `display_name(path)` -> Path(path).stem
pub fn display_name(path: &str) -> String {
    stem(path).to_string()
}
