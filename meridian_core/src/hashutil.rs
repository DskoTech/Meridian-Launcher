//! SHA-1 hex, used for media-server tokens (`token_for`) and thumbnail
//! cache keys (`_cache_path`). Both are just `sha1(s).hexdigest()`.

use sha1::{Digest, Sha1};

pub fn sha1_hex(s: &str) -> String {
    let mut h = Sha1::new();
    h.update(s.as_bytes());
    let digest = h.finalize();
    let mut out = String::with_capacity(40);
    for b in digest {
        out.push_str(&format!("{:02x}", b));
    }
    out
}
