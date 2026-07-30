//! Path helpers that reproduce Python `pathlib` semantics exactly, so the
//! Rust backend and the pure-Python fallback agree byte-for-byte on names,
//! stems and suffixes.
//!
//! IMPORTANT: at runtime the target is Windows, where `pathlib.Path` treats
//! BOTH `/` and `\` as separators. We therefore split on both here so the
//! native module matches Windows-Python. (On Linux, Python's PosixPath only
//! splits on `/`; the parity harness feeds forward-slash inputs so the two
//! agree there too.)

/// Final path component, splitting on `/` and `\` (Windows-compatible).
pub fn final_component(path: &str) -> &str {
    match path.rfind(['/', '\\']) {
        Some(i) => &path[i + 1..],
        None => path,
    }
}

/// `Path(name).suffix` — includes the leading dot, or "" if none.
/// pathlib rule: suffix = name[i:] only when `0 < i < len-1` for the last dot.
pub fn suffix(name: &str) -> &str {
    let comp = final_component(name);
    match comp.rfind('.') {
        Some(i) if i > 0 && i < comp.len() - 1 => &comp[i..],
        _ => "",
    }
}

/// Lowercased suffix (the form every extension set is compared against).
pub fn suffix_lower(name: &str) -> String {
    suffix(name).to_lowercase()
}

/// `Path(path).name`
#[allow(dead_code)]
pub fn name(path: &str) -> &str {
    final_component(path)
}

/// `Path(path).stem` — final component minus its suffix.
pub fn stem(path: &str) -> &str {
    let comp = final_component(path);
    match comp.rfind('.') {
        Some(i) if i > 0 && i < comp.len() - 1 => &comp[..i],
        _ => comp,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn suffix_matches_pathlib() {
        assert_eq!(suffix("foo.MP3"), ".MP3");
        assert_eq!(suffix("archive.tar.gz"), ".gz");
        assert_eq!(suffix(".bashrc"), "");
        assert_eq!(suffix("noext"), "");
        assert_eq!(suffix("trailingdot."), "");
        assert_eq!(suffix("dir/sub/file.txt"), ".txt");
    }

    #[test]
    fn stem_matches_pathlib() {
        assert_eq!(stem("C:/games/chrome.exe"), "chrome");
        assert_eq!(stem("a.b.c"), "a.b");
        assert_eq!(stem(".hidden"), ".hidden");
        assert_eq!(stem("plain"), "plain");
    }
}
