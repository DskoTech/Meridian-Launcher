//! Small pure formatting/categorization helpers: `fmt_duration` and
//! `_generic_icon_keyword_for` from the launcher's main.py.

use crate::pathutil::suffix_lower;

const MUSIC_EXT: &[&str] = &[".mp3", ".flac", ".wav", ".m4a", ".ogg", ".wma", ".aac"];
const PHOTO_EXT: &[&str] = &[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"];
const VIDEO_EXT: &[&str] = &[".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"];
const ARCHIVE_EXT: &[&str] = &[".zip", ".rar", ".7z", ".tar", ".gz"];
const INSTALLER_EXT: &[&str] = &[".exe", ".msi"];
const DOC_EXT: &[&str] = &[
    ".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx",
];

/// `fmt_duration(seconds)` -> "H:MM:SS" (with hours) or "M:SS".
pub fn fmt_duration(seconds: i64) -> String {
    let seconds = if seconds < 0 { 0 } else { seconds };
    let h = seconds / 3600;
    let rem = seconds % 3600;
    let m = rem / 60;
    let s = rem % 60;
    if h > 0 {
        format!("{}:{:02}:{:02}", h, m, s)
    } else {
        format!("{}:{:02}", m, s)
    }
}

/// Category icon keyword, matching `_generic_icon_keyword_for`'s exact order.
pub fn generic_icon_keyword(path: &str) -> String {
    let ext = suffix_lower(path);
    let e = ext.as_str();
    if PHOTO_EXT.contains(&e) {
        "photos"
    } else if VIDEO_EXT.contains(&e) {
        "videos"
    } else if MUSIC_EXT.contains(&e) {
        "music"
    } else if ARCHIVE_EXT.contains(&e) {
        "archive"
    } else if INSTALLER_EXT.contains(&e) {
        "apps"
    } else if DOC_EXT.contains(&e) {
        "document"
    } else {
        "generic"
    }
    .to_string()
}
