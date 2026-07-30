//! Native media server — replaces the file-serving half of main.py's
//! MediaHandler (the `/media?t=<token>` route, with HTTP Range support for
//! video seeking). It owns the token->path map that `token_for` / TOKEN_MAP
//! used to hold in Python.
//!
//! The pywebview-coupled routes (`/internal/open-explorer`,
//! `/internal/open-browser`, `/internal/plugin-exited`) are NOT here — they
//! call evaluate_js and stay on the Python server. This module serves only
//! media bytes, which is the throughput-sensitive part.

use std::collections::HashMap;
use std::fs::File;
use std::io::{Seek, SeekFrom};
use std::sync::{Mutex, OnceLock};
use std::thread;

use tiny_http::{Header, Response, Server, StatusCode};

use crate::hashutil::sha1_hex;

struct MediaState {
    tokens: Mutex<HashMap<String, String>>,
    port: u16,
}

static MEDIA: OnceLock<MediaState> = OnceLock::new();

fn header(name: &str, value: &str) -> Header {
    // These are all static, valid header names/values; unwrap is safe.
    Header::from_bytes(name.as_bytes(), value.as_bytes()).expect("valid header")
}

/// Register a filesystem path and return its media token (sha1 hex of the
/// path), matching Python's `token_for`. Idempotent.
pub fn register(path: &str) -> String {
    let token = sha1_hex(path);
    if let Some(state) = MEDIA.get() {
        if let Ok(mut map) = state.tokens.lock() {
            map.insert(token.clone(), path.to_string());
        }
    }
    token
}

/// The port the server is bound to, or 0 if not started.
pub fn port() -> u16 {
    MEDIA.get().map(|s| s.port).unwrap_or(0)
}

fn parse_range(range_header: &str, file_size: u64) -> (u64, u64) {
    // "bytes=start-end" — matches the lenient parsing in the Python handler.
    let after_eq = range_header.splitn(2, '=').nth(1).unwrap_or("");
    let mut parts = after_eq.splitn(2, '-');
    let start = parts.next().unwrap_or("").trim().parse::<u64>().unwrap_or(0);
    let end = match parts.next().map(|s| s.trim()) {
        Some(s) if !s.is_empty() => s.parse::<u64>().unwrap_or(file_size - 1),
        _ => file_size - 1,
    };
    let end = end.min(file_size.saturating_sub(1));
    (start, end)
}

fn handle(request: tiny_http::Request) {
    let url = request.url().to_string();

    // Only serve /media; anything else is 404 (internal routes live on the
    // Python server).
    let (path_part, query) = match url.split_once('?') {
        Some((p, q)) => (p, q),
        None => (url.as_str(), ""),
    };
    if path_part != "/media" {
        let _ = request.respond(Response::empty(StatusCode(404)));
        return;
    }

    // token from ?t=...
    let mut token = None;
    for kv in query.split('&') {
        if let Some(v) = kv.strip_prefix("t=") {
            token = Some(v.to_string());
            break;
        }
    }
    let token = match token {
        Some(t) => t,
        None => {
            let _ = request.respond(Response::empty(StatusCode(404)));
            return;
        }
    };

    let path = MEDIA
        .get()
        .and_then(|s| s.tokens.lock().ok().and_then(|m| m.get(&token).cloned()));
    let path = match path {
        Some(p) => p,
        None => {
            let _ = request.respond(Response::empty(StatusCode(404)));
            return;
        }
    };

    let meta = match std::fs::metadata(&path) {
        Ok(m) if m.is_file() => m,
        _ => {
            let _ = request.respond(Response::empty(StatusCode(404)));
            return;
        }
    };
    let file_size = meta.len();
    let mime = mime_guess::from_path(&path)
        .first_raw()
        .unwrap_or("application/octet-stream");

    let range_header = request
        .headers()
        .iter()
        .find(|h| h.field.as_str().as_str().eq_ignore_ascii_case("Range"))
        .map(|h| h.value.as_str().to_string());

    if file_size == 0 {
        // Nothing to serve; mirror a plain 200 with zero length.
        let resp = Response::empty(StatusCode(200))
            .with_header(header("Content-Type", mime))
            .with_header(header("Accept-Ranges", "bytes"))
            .with_header(header("Access-Control-Allow-Origin", "*"));
        let _ = request.respond(resp);
        return;
    }

    match range_header {
        Some(rh) => {
            let (start, end) = parse_range(&rh, file_size);
            let length = end - start + 1;
            let mut file = match File::open(&path) {
                Ok(f) => f,
                Err(_) => {
                    let _ = request.respond(Response::empty(StatusCode(404)));
                    return;
                }
            };
            if file.seek(SeekFrom::Start(start)).is_err() {
                let _ = request.respond(Response::empty(StatusCode(500)));
                return;
            }
            let reader = std::io::Read::take(file, length);
            let content_range = format!("bytes {}-{}/{}", start, end, file_size);
            let headers = vec![
                header("Content-Range", &content_range),
                header("Accept-Ranges", "bytes"),
                header("Content-Type", mime),
                header("Access-Control-Allow-Origin", "*"),
            ];
            let resp = Response::new(
                StatusCode(206),
                headers,
                reader,
                Some(length as usize),
                None,
            );
            let _ = request.respond(resp);
        }
        None => {
            let file = match File::open(&path) {
                Ok(f) => f,
                Err(_) => {
                    let _ = request.respond(Response::empty(StatusCode(404)));
                    return;
                }
            };
            // from_file streams the file (200 + Content-Length) without
            // reading it all into memory.
            let resp = Response::from_file(file)
                .with_header(header("Content-Type", mime))
                .with_header(header("Accept-Ranges", "bytes"))
                .with_header(header("Access-Control-Allow-Origin", "*"));
            let _ = request.respond(resp);
        }
    }
}

/// Bind 127.0.0.1:0, spawn the serving thread(s), and return the port.
/// Returns 0 on failure or if already started (call `port()` for the live
/// port). Uses a small worker pool so concurrent range requests (several
/// video/thumbnail loads at once) don't head-of-line block each other.
pub fn start() -> u16 {
    if let Some(state) = MEDIA.get() {
        return state.port; // already started
    }
    let server = match Server::http("127.0.0.1:0") {
        Ok(s) => s,
        Err(_) => return 0,
    };
    let port = match server.server_addr().to_ip() {
        Some(addr) => addr.port(),
        None => return 0,
    };
    if MEDIA
        .set(MediaState {
            tokens: Mutex::new(HashMap::new()),
            port,
        })
        .is_err()
    {
        return MEDIA.get().map(|s| s.port).unwrap_or(0);
    }

    use std::sync::Arc;
    let server = Arc::new(server);
    for _ in 0..4 {
        let server = Arc::clone(&server);
        thread::spawn(move || {
            for request in server.incoming_requests() {
                handle(request);
            }
        });
    }
    port
}
