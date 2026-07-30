//! meridian_core — native Rust backend shared by Meridian Launcher and
//! Meridian Game Library. Exposes the portable, hot-path backend logic
//! (filesystem scanning, hashing, formatting, settings-merge algorithms and
//! Playnite export parsing) to Python via PyO3. Everything that genuinely
//! requires Python/Windows (pywebview, pywin32 icon extraction, ffmpeg /
//! PIL / mutagen thumbnails, the GameInput controller stack, system_actions,
//! the media HTTP server) stays in Python and calls into this module.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

mod format;
mod hashutil;
mod indexpipeline;
mod media;
mod pathutil;
mod playnite;
mod scan;
mod settings;

use serde_json::Value;

fn parse_json(s: &str) -> PyResult<Value> {
    serde_json::from_str(s).map_err(|e| PyValueError::new_err(format!("invalid JSON: {e}")))
}

// ---- scanning ------------------------------------------------------------

#[pyfunction]
fn scan_dir(folder: &str, exts: Vec<String>) -> Vec<String> {
    scan::scan_dir(folder, &exts)
}

#[pyfunction]
#[pyo3(signature = (folder, exts=None))]
fn scan_flat(folder: &str, exts: Option<Vec<String>>) -> Vec<String> {
    scan::scan_flat(folder, exts.as_deref())
}

#[pyfunction]
fn list_subfolders(folder: &str) -> Vec<String> {
    scan::list_subfolders(folder)
}

#[pyfunction]
fn scan_with_mtimes(folders: Vec<String>, exts: Vec<String>) -> Vec<(String, f64)> {
    scan::scan_with_mtimes(&folders, &exts)
}

// ---- hashing / format ----------------------------------------------------

#[pyfunction]
fn sha1_hex(s: &str) -> String {
    hashutil::sha1_hex(s)
}

#[pyfunction]
fn fmt_duration(seconds: i64) -> String {
    format::fmt_duration(seconds)
}

#[pyfunction]
fn generic_icon_keyword(path: &str) -> String {
    format::generic_icon_keyword(path)
}

// ---- settings algorithms -------------------------------------------------

#[pyfunction]
fn deep_merge_json(base_json: &str, override_json: &str) -> PyResult<String> {
    let mut base = parse_json(base_json)?;
    let over = parse_json(override_json)?;
    settings::deep_merge(&mut base, &over);
    Ok(base.to_string())
}

#[pyfunction]
fn migrate_theme_media_json(json_str: &str) -> PyResult<String> {
    let mut v = parse_json(json_str)?;
    settings::migrate_theme_media(&mut v);
    Ok(v.to_string())
}

#[pyfunction]
fn slugify(name: &str) -> String {
    settings::slugify(name)
}

#[pyfunction]
fn display_name(path: &str) -> String {
    settings::display_name(path)
}

// ---- playnite ------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (raw_json, limit=5))]
fn playnite_recently_played(raw_json: &str, limit: usize) -> PyResult<String> {
    Ok(playnite::recently_played(&parse_json(raw_json)?, limit).to_string())
}

#[pyfunction]
fn playnite_library(raw_json: &str, store_key: &str) -> PyResult<String> {
    Ok(playnite::library(&parse_json(raw_json)?, store_key).to_string())
}

#[pyfunction]
fn playnite_other_sources(raw_json: &str) -> PyResult<String> {
    Ok(playnite::other_sources(&parse_json(raw_json)?).to_string())
}

#[pyfunction]
fn playnite_other_source_library(raw_json: &str, source_id: &str) -> PyResult<String> {
    Ok(playnite::other_source_library(&parse_json(raw_json)?, source_id).to_string())
}

#[pyfunction]
fn playnite_export_summary(raw_json: &str) -> PyResult<String> {
    Ok(playnite::export_summary(&parse_json(raw_json)?).to_string())
}

// ---- native media server -------------------------------------------------

#[pyfunction]
fn media_start() -> u16 {
    media::start()
}

#[pyfunction]
fn media_port() -> u16 {
    media::port()
}

#[pyfunction]
fn media_register(path: &str) -> String {
    media::register(path)
}

// ---- native index-cache pipeline -----------------------------------------

#[pyfunction]
fn index_prepare(kind: &str, cache_path: &str, current: Vec<(String, f64)>) -> Vec<String> {
    indexpipeline::prepare(kind, cache_path, current)
}

#[pyfunction]
fn index_finalize(kind: &str, new_entries_json: &str) -> Option<String> {
    indexpipeline::finalize(kind, new_entries_json)
}

#[pyfunction]
fn index_discard(kind: &str) {
    indexpipeline::discard(kind)
}

#[pymodule]
fn meridian_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(scan_dir, m)?)?;
    m.add_function(wrap_pyfunction!(scan_flat, m)?)?;
    m.add_function(wrap_pyfunction!(list_subfolders, m)?)?;
    m.add_function(wrap_pyfunction!(scan_with_mtimes, m)?)?;
    m.add_function(wrap_pyfunction!(sha1_hex, m)?)?;
    m.add_function(wrap_pyfunction!(fmt_duration, m)?)?;
    m.add_function(wrap_pyfunction!(generic_icon_keyword, m)?)?;
    m.add_function(wrap_pyfunction!(deep_merge_json, m)?)?;
    m.add_function(wrap_pyfunction!(migrate_theme_media_json, m)?)?;
    m.add_function(wrap_pyfunction!(slugify, m)?)?;
    m.add_function(wrap_pyfunction!(display_name, m)?)?;
    m.add_function(wrap_pyfunction!(playnite_recently_played, m)?)?;
    m.add_function(wrap_pyfunction!(playnite_library, m)?)?;
    m.add_function(wrap_pyfunction!(playnite_other_sources, m)?)?;
    m.add_function(wrap_pyfunction!(playnite_other_source_library, m)?)?;
    m.add_function(wrap_pyfunction!(playnite_export_summary, m)?)?;
    m.add_function(wrap_pyfunction!(media_start, m)?)?;
    m.add_function(wrap_pyfunction!(media_port, m)?)?;
    m.add_function(wrap_pyfunction!(media_register, m)?)?;
    m.add_function(wrap_pyfunction!(index_prepare, m)?)?;
    m.add_function(wrap_pyfunction!(index_finalize, m)?)?;
    m.add_function(wrap_pyfunction!(index_discard, m)?)?;
    Ok(())
}
