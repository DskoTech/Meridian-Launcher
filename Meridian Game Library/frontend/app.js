/* Meridian Game Library frontend — keyboard, mouse, and controller driven cross-bar UI.
 *
 * Navigation model (true "Xross Media Bar" style): the category row is
 * always live. Left/Right always changes the highlighted category, which
 * immediately refreshes the list shown below it. Up/Down always browses
 * the list currently shown. Confirm activates whatever is selected.
 *
 * Once you move past Apps, the category row becomes a circular carousel:
 * whichever category is highlighted slides into Apps' slot, and anything
 * that scrolls off the left loops back around to the right, behind System.
 */

const ICONS = {
  music: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/></svg>`,
  photos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5.5-5.5L9 17"/></svg>`,
  videos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="14" height="14" rx="2"/><path d="M17 9l4-2v10l-4-2"/></svg>`,
  apps: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
  games: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="8" width="20" height="9" rx="4"/><path d="M7 10.5v4M5 12.5h4"/><circle cx="16" cy="11" r="1"/><circle cx="18.5" cy="13.5" r="1"/></svg>`,
  emulators: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="6" y="6" width="12" height="12" rx="1.5"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>`,
  chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12a8 8 0 01-11.5 7.2L4 20l1-4.8A8 8 0 1121 12z"/></svg>`,
  streaming: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none"/></svg>`,
  web: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/></svg>`,
  files: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`,
  system: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v8"/><path d="M6.3 6.3a9 9 0 1011.4 0"/></svg>`,
  macros: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L4 14h6l-1 8 9-12h-6z"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.34 1.87l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.7 1.7 0 00-1.87-.34 1.7 1.7 0 00-1 1.56V21a2 2 0 11-4 0v-.09a1.7 1.7 0 00-1-1.56 1.7 1.7 0 00-1.87.34l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.7 1.7 0 00.34-1.87 1.7 1.7 0 00-1.56-1H3a2 2 0 110-4h.09a1.7 1.7 0 001.56-1 1.7 1.7 0 00-.34-1.87l-.06-.06a2 2 0 112.83-2.83l.06.06a1.7 1.7 0 001.87.34H9a1.7 1.7 0 001-1.56V3a2 2 0 114 0v.09a1.7 1.7 0 001 1.56 1.7 1.7 0 001.87-.34l.06-.06a2 2 0 112.83 2.83l-.06.06a1.7 1.7 0 00-.34 1.87V9a1.7 1.7 0 001.56 1H21a2 2 0 110 4h-.09a1.7 1.7 0 00-1.56 1z"/></svg>`,
  generic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`,
  power: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v8"/><path d="M6.3 6.3a9 9 0 1011.4 0"/></svg>`,
  sleep: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>`,
  hibernate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v20M2 12h20M5 5l14 14M19 5L5 19"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6L6 18"/></svg>`,
  controlpanel: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="1.6" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="10" cy="18" r="1.6" fill="currentColor" stroke="none"/></svg>`,
  taskmanager: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h4M7 13h10M7 17h6"/></svg>`,
  bat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l3 3v17H6z"/><path d="M10 10h4M10 14h4"/></svg>`,
  recyclebin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M6 7l1 13a2 2 0 002 2h6a2 2 0 002-2l1-13"/><path d="M10 11v6M14 11v6"/></svg>`,
  uninstallapps: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M15 17l5 5M20 17l-5 5"/></svg>`,
  wifi: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 8.5a16 16 0 0120 0M5.5 12a11 11 0 0113 0M9 15.5a6 6 0 016 0"/><circle cx="12" cy="19" r="1.2" fill="currentColor" stroke="none"/></svg>`,
  bluetooth: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7l10 10-5 5V2l5 5L7 17"/></svg>`,
  steam: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="9" cy="15" r="2.4"/><path d="M11 13l4-4"/><circle cx="16" cy="8" r="2.2"/></svg>`,
  gog: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M8 10v6M8 13h3M15 10a2.5 2.5 0 100 6 2.5 2.5 0 000-6z"/></svg>`,
  epic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 3h12v13l-6 5-6-5z"/><path d="M9 8h6M9 12h6"/></svg>`,
  luna: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 14.5A8.5 8.5 0 119.5 4a7 7 0 1010.5 10.5z"/></svg>`,
  other: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>`,
};

const PALETTE = ["#60a5fa", "#f472b6", "#34d399", "#fb923c", "#e879f9", "#facc15", "#c084fc", "#38bdf8"];

// Per-storefront wiring for the shared game-grid renderer: which Api methods
// to call and how to talk about install/uninstall, since not every store
// hands off the same way (Steam has steam:// protocol hand-off; GOG has no
// equivalent, so "install" opens the download page instead — see
// gog_integration.py for why).
// All four storefronts are backed by the same Playnite library export now
// (see playnite_import.py) — this app reads what Playnite already knows
// instead of talking to each store directly, and hands actions back to
// Playnite via its playnite:// URI protocol. Since install/uninstall both
// just open the game's page in Playnite (there's no documented URI action
// for either — only launch), all four configs are genuinely identical
// apart from label and API method prefix, so build them from one template
// rather than hand-duplicating near-identical blocks four times.
function makeStoreConfig(storeKey, label) {
  return {
    label,
    api: {
      login: `${storeKey}_login`, getLibrary: `${storeKey}_get_library`, syncLibrary: `${storeKey}_sync_library`,
      install: storeKey === "gog" ? "gog_open_download_page" : `${storeKey}_install`,
      uninstall: `${storeKey}_uninstall`, launch: `${storeKey}_launch`,
    },
    installLabel: "Install with Playnite",
    installingText: (title) => `Opening ${title} \u2026`,
    uninstallLabel: "Play Game",
    uninstallConfirmText: () => null, // this is now a launch action, not destructive
    uninstallingText: (title) => `Launching ${title}\u2026`,
    settingsKey: "playnite",
    loggedInCheck: (s) => (s.game_import_source === "heroic") ? !!s.heroic_available : !!(s.playnite && s.playnite.export_available),
    loginButtonLabel: "Check Playnite connection",
    loginStartMessage: () => "Checking for a Playnite library export\u2026",
    loginSubtext: "Press confirm to check whether Meridian Game Library can see your Playnite library yet",
  };
}

const STORE_CONFIG = {
  steam: makeStoreConfig("steam", "Steam"),
  gog: makeStoreConfig("gog", "GOG"),
  epic: makeStoreConfig("epic", "Epic Games"),
  amazon: makeStoreConfig("amazon", "Luna"),
  other: makeStoreConfig("other", "Other"),
};

// Filter-preset sections reuse the whole game_grid pipeline; the only
// real differences are (a) the library fetch needs the preset id, handled
// by refreshGameGridPanel branching to pnfilter_get_library, and (b)
// launch/install go through the preset-agnostic pnfilter_* Api methods,
// since a game in a preset is still just a Playnite game.
function makeFilterPresetConfig(label) {
  return {
    ...makeStoreConfig("pnfilter", label),
    api: {
      login: "playnite_status",
      getLibrary: null, // never called directly — refreshGameGridPanel handles presets itself
      syncLibrary: "pnfilter_touch",
      install: "pnfilter_install",
      uninstall: "pnfilter_launch",
      launch: "pnfilter_launch",
    },
  };
}

function storeConfigFor(cat) {
  if (cat && cat.preset != null) return makeFilterPresetConfig(cat.label);
  return STORE_CONFIG[cat.store];
}

// Note: Settings and System are appended in buildCategories(), in that
// order, so System always sits after Settings as the very last category.
const FIXED_CATEGORIES = [
  { id: "steam", label: "Steam", kind: "game_grid", store: "steam", color: "var(--accent-steam)" },
  { id: "gog", label: "GOG", kind: "game_grid", store: "gog", color: "var(--accent-gog)" },
  { id: "epic", label: "Epic", kind: "game_grid", store: "epic", color: "var(--accent-epic)" },
  { id: "luna", label: "Luna", kind: "game_grid", store: "amazon", color: "var(--accent-amazon)" },
  { id: "other", label: "Other", kind: "game_grid", store: "other", color: "var(--accent-other)" },
];

// Files: Meridian Explorer first, Windows File Explorer second.
const FILE_ITEMS = [
  { id: "meridian_explorer", label: "Meridian Explorer", icon: "files" },
  { id: "windows_explorer", label: "Windows File Explorer", icon: "files" },
];

// Safe-first: a stray confirm press lands on something harmless (Task
// Manager), not something destructive (Shut Down is last).
const SYSTEM_ITEMS = [
  { id: "taskmanager", label: "Task Manager", icon: "taskmanager" },
  { id: "controlpanel", label: "Control Panel", icon: "controlpanel" },
  { id: "recyclebin", label: "Recycle Bin", icon: "recyclebin" },
  { id: "uninstallapps", label: "Uninstall Apps", icon: "uninstallapps" },
  { id: "wifi", label: "Wi-Fi", icon: "wifi" },
  { id: "bluetooth", label: "Bluetooth", icon: "bluetooth" },
  { id: "close", label: "Close Program", icon: "close" },
  { id: "sleep", label: "Sleep", icon: "sleep" },
  { id: "hibernate", label: "Hibernate", icon: "hibernate" },
  { id: "shutdown", label: "Shut Down", icon: "power" },
];

// Carousel pivots at Apps (index 3): categories at/before it render in a
// fixed, normal left-to-right row; past it, the row becomes circular with
// the current category always sliding into Apps' slot.
const CAROUSEL_ANCHOR = 3;

const state = {
  categories: [],
  catIndex: 0,
  items: [],
  selected: 0,
  settings: null,
  playIndex: -1,
  keyboardControls: null,
  introDismissed: false,
  folderStack: { music: [], photos: [], videos: [] }, // subfolder browsing, per kind
  gameFilter: {}, // per category id: "all" | "installed" | "not_installed"
  gameLibraryFull: {}, // per category id: unfiltered entries, so filtering doesn't need a refetch
  filterPresets: [], // [{id, name, count}] saved Playnite filter presets, when that toggle is on
  gridFocus: "list", // "list" | "filter" — which pane has directional focus in a game_grid section
  radialFocus: "sections", // "sections" | "options" | "subfolder" — sections/filter focus cycle
  sectionsBrowseIndex: 0, // which section is highlighted while browsing, until confirmed
};

const el = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Windows paths (e.g. from Playnite's cover art export) are resolved to
// ready-to-use URLs server-side, through the app's existing local media
// server (see main.py's media_url/_entries_with_media_urls) — raw file://
// URLs to arbitrary paths outside the app's own frontend folder aren't
// reliable in this webview backend, so the frontend never has to build one.

// ---------------- clock & battery ----------------

function tickClock() {
  el("clock").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
setInterval(tickClock, 15000);

async function updateBatteryIndicator() {
  const ind = el("battery-indicator");
  const settings = state.settings;
  if (!settings || !settings.battery_indicator) { ind.classList.add("hidden"); return; }
  const status = await api().get_battery_status();
  if (!status) { ind.classList.add("hidden"); return; }
  ind.classList.remove("hidden");
  el("battery-pct").textContent = `${status.percent}%`;
  ind.classList.toggle("charging", !!status.plugged);
  ind.classList.toggle("low", !status.plugged && status.percent <= 20);
  const fillWidth = Math.max(1, Math.round((status.percent / 100) * 18));
  el("battery-fill").setAttribute("width", String(fillWidth));
}
setInterval(updateBatteryIndicator, 30000);

// ---------------- category list (fixed + custom + settings + system) ----------------

// Playnite filter-preset sections: one section per saved Playnite filter
// preset (see set_playnite_filter_sections / the MeridianExporter
// extension), slotted after the fixed storefront sections. Presets are
// fetched once into state.filterPresets (loadFilterPresets) rather than
// per-build, since buildCategories has to stay synchronous.
function filterPresetCategories(settings) {
  if (!settings || !settings.playnite_filter_sections) return [];
  if ((settings.game_import_source || "playnite") !== "playnite") return [];
  return (state.filterPresets || []).map((p, i) => ({
    id: `pnfilter_${p.id}`,
    label: p.name,
    kind: "game_grid",
    store: "pnfilter",
    preset: p.id,
    color: PALETTE[i % PALETTE.length],
  }));
}

function buildCategories(settings) {
  return [
    ...FIXED_CATEGORIES,
    ...filterPresetCategories(settings),
    { id: "settings", label: "Settings", kind: "settings", color: "var(--accent-settings)" },
  ];
}

async function loadFilterPresets(settings) {
  if (settings && settings.playnite_filter_sections && (settings.game_import_source || "playnite") === "playnite") {
    try {
      state.filterPresets = (await api().playnite_filter_presets()) || [];
    } catch (e) {
      state.filterPresets = [];
    }
  } else {
    state.filterPresets = [];
  }
}

function iconFor(catId) {
  return ICONS[catId] || ICONS.generic;
}

// ---------------- category row: circular carousel with FLIP sliding ----------------

const categoryElements = new Map(); // id -> persistent DOM node, so transitions can animate

function currentHighlightIndex() {
  return state.radialFocus === "sections" ? state.sectionsBrowseIndex : state.catIndex;
}

function computeDisplayOrder() {
  const n = state.categories.length;
  const anchor = currentHighlightIndex();
  const start = anchor <= CAROUSEL_ANCHOR ? 0 : anchor - CAROUSEL_ANCHOR;
  const order = [];
  for (let i = 0; i < n; i++) order.push((start + i) % n);
  return order;
}

function ensureCategoryElement(cat) {
  let wrap = categoryElements.get(cat.id);
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "category";
    wrap.addEventListener("click", () => {
      const idx = state.categories.findIndex((c) => c.id === cat.id);
      if (idx !== -1) selectCategory(idx);
    });
    categoryElements.set(cat.id, wrap);
  }
  wrap.style.setProperty("--cat-color", cat.color);
  wrap.innerHTML = `<div class="icon-ring">${iconFor(cat.id)}</div><div class="label">${escapeHtml(cat.label)}</div>`;
  return wrap;
}

function renderCategories() {
  const row = el("category-row");

  // drop persistent elements for categories that no longer exist (e.g. a removed custom section)
  const currentIds = new Set(state.categories.map((c) => c.id));
  for (const id of [...categoryElements.keys()]) {
    if (!currentIds.has(id)) categoryElements.delete(id);
  }

  const order = computeDisplayOrder();
  const highlightIdx = currentHighlightIndex();

  // FLIP part 1: record where each visible element currently sits
  const oldRects = new Map();
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const existing = categoryElements.get(cat.id);
    if (existing && existing.parentElement === row) oldRects.set(cat.id, existing.getBoundingClientRect());
  });

  // Rebuild in the new circular order (existing nodes are moved, not recreated)
  const frag = document.createDocumentFragment();
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const wrap = ensureCategoryElement(cat);
    wrap.classList.toggle("active", realIdx === highlightIdx);
    wrap.classList.toggle("pending-confirm", realIdx === highlightIdx && highlightIdx !== state.catIndex);
    frag.appendChild(wrap);
  });
  row.innerHTML = "";
  row.appendChild(frag);

  // CyberRadial: the active category is always pinned to angle 0 (the
  // fixed point straight out from the hub's center, pill pointing back
  // in) — everything else's angle is just "how many positions away from
  // active", so moving up/down rotates neighbors into that fixed spot.
  // Harmless no-op in NightHorizon (angle unused there).
  const activePos = order.indexOf(highlightIdx);
  const ORBIT_STEP_DEG = 20;
  const ORBIT_FADE_RANGE = 5; // matches where clamping kicks in (90/20=4.5) so nothing visible ever shares a clamped angle
  order.forEach((realIdx, i) => {
    const cat = state.categories[realIdx];
    const elx = categoryElements.get(cat.id);
    const offset = i - activePos;
    const angle = Math.max(-90, Math.min(90, offset * ORBIT_STEP_DEG));
    const fade = Math.max(0, 1 - Math.abs(offset) / ORBIT_FADE_RANGE);
    elx.style.setProperty("--orbit-angle", angle + "deg");
    elx.style.setProperty("--orbit-fade", fade.toFixed(3));
  });

  // FLIP part 2: animate from the old position to the new one. CyberRadial
  // positions categories via CSS left/top (transitioned in the stylesheet)
  // driven by --orbit-angle, so this transform-based trick is skipped
  // there — an inline transform would clobber the orbit's own positioning
  // transform.
  if (isCyberRadial()) return;
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const elx = categoryElements.get(cat.id);
    const oldRect = oldRects.get(cat.id);
    if (!oldRect) { elx.style.transition = ""; elx.style.transform = ""; return; }
    const newRect = elx.getBoundingClientRect();
    const dx = oldRect.left - newRect.left;
    const dy = oldRect.top - newRect.top;
    if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
      elx.style.transition = "none";
      elx.style.transform = `translate(${dx}px, ${dy}px)`;
      requestAnimationFrame(() => {
        elx.style.transition = "transform 320ms ease";
        elx.style.transform = "translate(0, 0)";
      });
    } else {
      elx.style.transition = "";
      elx.style.transform = "";
    }
  });
}

// Keep the currently-highlighted category icon horizontally aligned with
// the icon column of whatever list is showing below it, regardless of
// section (measured live rather than hand-tuned, so it stays correct even
// as row/list content varies).
function alignCategoryRowToList() {
  // The row now centers itself via CSS (justify-content: center) instead
  // of being nudged into alignment with whatever's first in the list
  // below — that old trick was built around the single-column list
  // layout and didn't apply to game_grid tiles or Settings anyway.
  el("category-row").style.transform = "none";
}

function applyAccent() {
  document.documentElement.style.setProperty("--active-accent", state.categories[state.catIndex].color);
  applyLayoutClass();
}

// Layout mode: "night_horizon" (default) is the hub/orbit sidebar look;
// "cyber_radial" rearranges the same DOM into the orbital-arc variant.
// Purely a CSS concern driven by one body class — see style.css. The
// grid's own left/right/up/down navigation (handleDirectionalLeft etc.)
// is unchanged either way — CyberRadial here is a visual reflow only.
function isCyberRadial() {
  return !!(state.settings && state.settings.layout === "cyber_radial");
}
function isDawningHorizon() {
  return !!(state.settings && (state.settings.layout === "dawning_horizon" || !state.settings.layout));
}
// ---------------- Dawning Horizon: primary theme color ----------------
// "original" leaves the stylesheet's values alone. Anything else is
// "<palette>:<hue>": the background is re-tinted to that hue in that
// palette's saturation/lightness, and the per-section accents are
// reassigned as a ROYGBIV rainbow rotated to start at the background's
// complement — so the sections always read against the background rather
// than dissolving into it. All computed here and applied as inline CSS
// custom properties on <body>, which out-specifies the
// body.layout-dawninghorizon class block without touching the stylesheet.

const DAWNING_HUES = [
  ["red", 0], ["orange", 28], ["yellow", 52], ["green", 125],
  ["blue", 215], ["indigo", 255], ["violet", 285],
];

// Per-palette recipe: background stops, accent chroma, and whether the
// background is light enough to need dark text swapped in.
const DAWNING_PALETTES = {
  light:     { bg0: [40, 90], bg1: [46, 82], accent: [72, 38], lightBg: true },
  dark:      { bg0: [55, 6],  bg1: [50, 13], accent: [78, 64], lightBg: false },
  neon:      { bg0: [95, 5],  bg1: [100, 15], accent: [100, 60], lightBg: false },
  primary:   { bg0: [85, 26], bg1: [92, 40], accent: [95, 68], lightBg: false },
  pastel:    { bg0: [55, 91], bg1: [60, 84], accent: [52, 48], lightBg: true },
  bubblegum: { bg0: [82, 80], bg1: [90, 70], accent: [88, 42], lightBg: true },
};

function parseDawningThemeColor(settings) {
  const raw = (settings && settings.dawning_theme_color) || "original";
  if (raw === "original") return null;
  const [palette, hueName] = raw.split(":");
  const pal = DAWNING_PALETTES[palette];
  const hueEntry = DAWNING_HUES.find(([name]) => name === hueName);
  if (!pal || !hueEntry) return null;
  return { palette: pal, hue: hueEntry[1] };
}

function applyDawningThemeColor(settings) {
  const body = document.body;
  const clear = () => {
    ["--bg-0", "--bg-1", "--text-hi", "--text-lo", "--panel", "--line"].forEach((v) => body.style.removeProperty(v));
    DAWNING_ACCENT_VARS.forEach((name) => body.style.removeProperty(`--accent-${name}`));
  };
  const theme = isDawningHorizon() ? parseDawningThemeColor(settings) : null;
  if (!theme) { clear(); return; }

  const { palette: pal, hue } = theme;
  const hsl = (h, s, l) => `hsl(${((h % 360) + 360) % 360}, ${s}%, ${l}%)`;
  body.style.setProperty("--bg-0", hsl(hue, pal.bg0[0], pal.bg0[1]));
  body.style.setProperty("--bg-1", hsl(hue, pal.bg1[0], pal.bg1[1]));

  // Light backgrounds need the text/panel/hairline colors flipped too, or
  // the original light-on-dark text vanishes.
  if (pal.lightBg) {
    body.style.setProperty("--text-hi", hsl(hue, 30, 12));
    body.style.setProperty("--text-lo", hsl(hue, 18, 34));
    body.style.setProperty("--panel", "rgba(255, 255, 255, 0.55)");
    body.style.setProperty("--line", "rgba(15, 23, 42, 0.18)");
  }

  // ROYGBIV accents, rotated so the rainbow starts at the background's
  // complementary hue and cycles from there.
  const shift = hue + 180 - DAWNING_HUES[0][1];
  DAWNING_ACCENT_VARS.forEach((name, i) => {
    const base = DAWNING_HUES[i % DAWNING_HUES.length][1];
    body.style.setProperty(`--accent-${name}`, hsl(base + shift, pal.accent[0], pal.accent[1]));
  });
}

// Every per-section accent variable the Dawning stylesheet defines, in the
// order they get rainbow hues. --active-accent itself follows whichever of
// these the selected category points at, so it needs no direct handling.
const DAWNING_ACCENT_VARS = [
  "steam", "gog", "epic", "amazon", "other", "settings", "music",
];

function applyLayoutClass() {
  document.body.classList.toggle("layout-cyberradial", isCyberRadial());
  document.body.classList.toggle("layout-dawninghorizon", isDawningHorizon());
  document.body.classList.toggle("layout-nighthorizon", !isCyberRadial() && !isDawningHorizon());
  applyDawningThemeColor(state.settings);
}

// ---------------- category selection (always live, no separate "enter" step) ----------------

function selectCategory(i) {
  state.catIndex = i;
  state.selected = 0;
  state.gridFocus = "list";
  state.radialFocus = "sections";
  state.sectionsBrowseIndex = i;
  applyAccent();
  renderCategories();
  refreshItemPanel();
}

function moveCategory(delta) {
  const next = (state.catIndex + delta + state.categories.length) % state.categories.length;
  selectCategory(next);
}

function isGameGridCategory() {
  const cat = state.categories[state.catIndex];
  return !!cat && cat.kind === "game_grid";
}

// Must match the grid's column count in style.css (.channel-grid's
// grid-template-columns: repeat(5, 1fr)) — if that ever changes, update
// this too so Up/Down keep landing in the same visual column.
function GRID_COLUMNS_NOW() { return (state.settings && state.settings.games_per_row) || 5; }

function currentGridRowBounds() {
  const rowStart = Math.floor(state.selected / GRID_COLUMNS_NOW()) * GRID_COLUMNS_NOW();
  const rowEnd = Math.min(rowStart + GRID_COLUMNS_NOW() - 1, state.items.length - 1);
  return { rowStart, rowEnd };
}

// Up/down always browses whichever level has focus: sections (browse-only,
// confirm to load), or the game grid/filter sidebar once a section is
// loaded. Left/right only move within the grid now — they no longer
// change sections or jump to the filter sidebar; that's Y/\ (forward) and
// B/Space (back) exclusively, so there's one predictable way to reach
// each panel instead of several overlapping ones.
function handleDirectionalLeft() {
  if (state.radialFocus === "sections") return;
  if (isGameGridCategory() && state.gridFocus === "list") {
    const { rowStart } = currentGridRowBounds();
    if (state.selected > rowStart) moveSelection(-1);
    return;
  }
}
function handleDirectionalRight() {
  if (state.radialFocus === "sections") return;
  if (isGameGridCategory() && state.gridFocus === "list") {
    const { rowEnd } = currentGridRowBounds();
    if (state.selected < rowEnd) moveSelection(1);
    return;
  }
}
function handleDirectionalUp() {
  if (state.radialFocus === "sections") {
    const n = state.categories.length;
    state.sectionsBrowseIndex = (state.sectionsBrowseIndex - 1 + n) % n;
    renderCategories();
    return;
  }
  if (isGameGridCategory() && state.gridFocus === "filter") { moveFilterSelection(-1); return; }
  if (isGameGridCategory() && state.gridFocus === "list") { moveSelection(-GRID_COLUMNS_NOW()); return; }
  moveSelection(-1);
}
function handleDirectionalDown() {
  if (state.radialFocus === "sections") {
    const n = state.categories.length;
    state.sectionsBrowseIndex = (state.sectionsBrowseIndex + 1) % n;
    renderCategories();
    return;
  }
  if (isGameGridCategory() && state.gridFocus === "filter") { moveFilterSelection(1); return; }
  if (isGameGridCategory() && state.gridFocus === "list") { moveSelection(GRID_COLUMNS_NOW()); return; }
  moveSelection(1);
}

// Confirm out of "sections": load the browsed-to section only if it's
// different from what's already loaded (going back to sections and
// re-confirming the same one shouldn't refetch/rebuild anything).
function commitBrowsedSection() {
  if (state.sectionsBrowseIndex !== state.catIndex) {
    state.catIndex = state.sectionsBrowseIndex;
    state.selected = 0;
    state.gridFocus = "list";
    applyAccent();
    renderCategories();
    refreshItemPanel();
  }
  state.radialFocus = "options";
  renderCategories();
}

// Y (quick press) / \ key: jump to the filter sidebar, same idea as
// Meridian Launcher's jump-to-subfolder.
function handleJumpToSubfolder() {
  if (state.radialFocus === "sections") return;
  if (isGameGridCategory() && state.gridFocus !== "filter") {
    state.gridFocus = "filter";
    renderGameFilterSidebar(state.categories[state.catIndex]);
  }
}

function moveSelection(delta) {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "settings" || cat.kind === "direct") return; // no linear list to browse there
  if (!state.items.length) return;
  state.selected = Math.max(0, Math.min(state.items.length - 1, state.selected + delta));
  renderItemList(cat);
}

// ---------------- filling the panel for whatever category is highlighted ----------------

async function refreshItemPanel() {
  const cat = state.categories[state.catIndex];
  try {
    if (cat.kind === "direct") { renderDirectInfo(cat); return; }
    if (cat.kind === "settings") { el("subfolder-nav").classList.add("hidden"); el("preview-pane").classList.add("hidden"); await renderSettings(); return; }

    el("item-panel").innerHTML = `<div class="empty-msg">Loading&hellip;</div>`;

    if (cat.kind === "system_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      state.items = SYSTEM_ITEMS;
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "file_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      state.items = FILE_ITEMS;
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "media") {
      if (state.settings && state.settings.load_subfolders === false) {
        await refreshMediaBrowseView(cat.id);
      } else {
        el("subfolder-nav").classList.add("hidden");
        const items = await api().scan_library(cat.id);
        state.items = items.length ? items : [{ __empty: true }];
        state.selected = Math.min(state.selected, state.items.length - 1);
        renderItemList(cat);
      }
    } else if (cat.kind === "game_grid") {
      el("preview-pane").classList.add("hidden");
      await refreshGameGridPanel(cat);
    } else if (cat.kind === "exe_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      const items = await api().list_section_items(cat.id);
      state.items = items.length ? items : [{ __empty: true }];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "macro_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      const items = await api().list_macro_items();
      state.items = items;
      state.selected = Math.min(state.selected, Math.max(items.length - 1, 0));
      renderItemList(cat);
    }
  } catch (err) {
    console.error("Failed to load section:", cat.id, err);
    el("item-panel").innerHTML = `<div class="empty-msg">Something went wrong loading ${escapeHtml(cat.label)}.<br>${escapeHtml(err && err.message ? err.message : String(err))}</div>`;
    alignCategoryRowToList();
  }
}

function renderDirectInfo(cat) {
  el("subfolder-nav").classList.add("hidden");
  el("preview-pane").classList.add("hidden");
  el("item-panel").innerHTML = `<div class="empty-msg">Press confirm to open your default web browser.</div>`;
  alignCategoryRowToList();
}

// ---------------- subfolder browsing (Load Subfolders disabled) ----------------

async function refreshMediaBrowseView(kind) {
  const roots = await api().get_root_folders(kind);
  if (!roots.length) {
    el("subfolder-nav").classList.add("hidden");
    el("preview-pane").classList.add("hidden");
    state.items = [{ __empty: true }];
    state.selected = 0;
    renderItemList(state.categories[state.catIndex]);
    return;
  }
  el("subfolder-nav").classList.remove("hidden");
  if (!state.folderStack[kind] || !state.folderStack[kind].length) {
    state.folderStack[kind] = [roots[0]];
  }
  await loadCurrentBrowsePath(kind);
}

async function loadCurrentBrowsePath(kind) {
  const stack = state.folderStack[kind];
  const path = stack[stack.length - 1];
  const [result, roots] = await Promise.all([api().browse_folder(kind, path), api().get_root_folders(kind)]);
  state.subfoldersCurrent = result.subfolders;
  state.items = result.items.length ? result.items : [{ __empty: true, __browsingEmpty: true }];
  state.selected = 0;
  renderSubfolderSidebar(kind, roots);
  renderItemList(state.categories[state.catIndex]);
}

async function enterSubfolder(kind, name) {
  const stack = state.folderStack[kind];
  const current = stack[stack.length - 1];
  const sep = current.includes("\\") ? "\\" : "/";
  stack.push(current.replace(/[\\/]+$/, "") + sep + name);
  await loadCurrentBrowsePath(kind);
}

async function goUpFolder(kind) {
  const stack = state.folderStack[kind];
  if (!stack || stack.length <= 1) return false;
  stack.pop();
  await loadCurrentBrowsePath(kind);
  return true;
}

const FOLDER_ICON_SVG = `<svg class="sf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`;
const UP_ICON_SVG = `<svg class="sf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`;

function renderSubfolderSidebar(kind, roots) {
  const nav = el("subfolder-nav");
  nav.innerHTML = `<div class="sf-header">Folders</div>`;
  const stack = state.folderStack[kind] || [];
  const currentRoot = stack[0];

  roots.forEach((r) => {
    const row = document.createElement("div");
    row.className = "sf-row" + (r === currentRoot ? " selected" : "");
    const label = r.split(/[\\/]/).filter(Boolean).pop() || r;
    row.innerHTML = `${FOLDER_ICON_SVG}<span class="sf-label">${escapeHtml(label)}</span>`;
    row.addEventListener("click", async () => { state.folderStack[kind] = [r]; await loadCurrentBrowsePath(kind); });
    nav.appendChild(row);
  });

  if (stack.length > 1) {
    const up = document.createElement("div");
    up.className = "sf-row";
    up.innerHTML = `${UP_ICON_SVG}<span class="sf-label">.. Up</span>`;
    up.addEventListener("click", () => goUpFolder(kind));
    nav.appendChild(up);
  }

  (state.subfoldersCurrent || []).forEach((name) => {
    const row = document.createElement("div");
    row.className = "sf-row";
    row.innerHTML = `${FOLDER_ICON_SVG}<span class="sf-label">${escapeHtml(name)}</span>`;
    row.addEventListener("click", () => enterSubfolder(kind, name));
    nav.appendChild(row);
  });
}

// ---------------- bigger preview pane (Music/Photos/Videos) ----------------

function updatePreviewPane() {
  const cat = state.categories[state.catIndex];
  const pane = el("preview-pane");
  if (!cat || cat.kind !== "media") { pane.classList.add("hidden"); return; }
  const item = state.items[state.selected];
  if (!item || item.__empty) { pane.classList.add("hidden"); return; }
  pane.classList.remove("hidden");
  el("preview-img").src = item.fullUrl || item.thumbUrl || "";
  el("preview-title").textContent = item.title || item.name || "";
}

// ---------------- one unified row renderer for every section kind ----------------

// ---------------- Steam / game-storefront grid sections ----------------

let _chimeCtx = null;
function playChime() {
  try {
    _chimeCtx = _chimeCtx || new (window.AudioContext || window.webkitAudioContext)();
    const ctx = _chimeCtx;
    const now = ctx.currentTime;
    [523.25, 659.25].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const start = now + i * 0.09;
      gain.gain.setValueAtTime(0, start);
      gain.gain.linearRampToValueAtTime(0.14, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.35);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.4);
    });
  } catch (e) { /* audio not available — silently skip */ }
}

function applyGameFilter(catId, entries) {
  const filter = state.gameFilter[catId] || "all";
  if (filter === "installed") return entries.filter((e) => e.installed);
  if (filter === "not_installed") return entries.filter((e) => !e.installed);
  return entries;
}

const GAME_FILTER_OPTIONS = [
  { id: "all", label: "All Games" },
  { id: "installed", label: "Installed" },
  { id: "not_installed", label: "Not Installed" },
];

function applyGameFilterAndRerender(cat, filterId, optionLabel) {
  state.gameFilter[cat.id] = filterId;
  const full = state.gameLibraryFull[cat.id] || [];
  const filtered = applyGameFilter(cat.id, full);
  state.items = filtered.length ? filtered : [{ __empty: true, message: `No ${(optionLabel || filterId).toLowerCase()} to show` }];
  state.selected = 0;
  renderGameFilterSidebar(cat);
  renderItemList(cat);
}

function moveFilterSelection(delta) {
  const cat = state.categories[state.catIndex];
  if (!cat || cat.kind !== "game_grid") return;
  const current = state.gameFilter[cat.id] || "all";
  const idx = GAME_FILTER_OPTIONS.findIndex((o) => o.id === current);
  const nextIdx = ((idx === -1 ? 0 : idx) + delta + GAME_FILTER_OPTIONS.length) % GAME_FILTER_OPTIONS.length;
  const next = GAME_FILTER_OPTIONS[nextIdx];
  applyGameFilterAndRerender(cat, next.id, next.label);
}

function renderGameFilterSidebar(cat) {
  const nav = el("subfolder-nav");
  const focused = state.gridFocus === "filter";
  nav.className = focused ? "focused" : "";
  nav.innerHTML = `<div class="sf-header">Show</div>`;
  const current = state.gameFilter[cat.id] || "all";
  GAME_FILTER_OPTIONS.forEach((opt) => {
    const row = document.createElement("div");
    row.className = "sf-row" + (opt.id === current ? " selected" : "");
    row.innerHTML = `<span class="sf-label">${opt.label}</span>`;
    row.addEventListener("click", () => {
      state.gridFocus = "filter";
      applyGameFilterAndRerender(cat, opt.id, opt.label);
    });
    nav.appendChild(row);
  });
  nav.classList.remove("hidden");
}

async function refreshGameGridPanel(cat) {
  const settings = state.settings || (await api().get_settings());
  state.settings = settings;
  const cfg = storeConfigFor(cat);

  // Playnite filter-preset section: same grid, same filter sidebar, but
  // the entries come from pnfilter_get_library(preset id). Re-read on
  // every visit — it's a local file read, effectively instant.
  if (cat.preset != null) {
    const res = await api().pnfilter_get_library(cat.preset);
    const entries = (res && res.entries) || [];
    state.gameLibraryFull[cat.id] = entries;
    const filtered = applyGameFilter(cat.id, entries);
    state.items = filtered.length ? filtered : [{ __empty: true, message: `No games match the "${cat.label}" Playnite filter yet \u2014 adjust the preset in Playnite, then re-export.` }];
    state.selected = Math.min(state.selected, state.items.length - 1);
    renderGameFilterSidebar(cat);
    renderItemList(cat);
    return;
  }

  if (!cfg.loggedInCheck(settings)) {
    el("subfolder-nav").classList.add("hidden");
    state.items = [{ __storeLogin: true, __store: cat.store }];
    state.selected = 0;
    renderItemList(cat);
    return;
  }

  const cached = await api()[cfg.api.getLibrary]();
  const cachedEntries = cached.entries || [];
  state.gameLibraryFull[cat.id] = cachedEntries;
  const filtered = applyGameFilter(cat.id, cachedEntries);
  state.items = filtered.length ? filtered : [{ __empty: true, message: `Syncing your ${cfg.label} library\u2026` }];
  state.selected = Math.min(state.selected, state.items.length - 1);
  renderGameFilterSidebar(cat);
  renderItemList(cat);

  // Refresh in the background so the tiles are never stale for long, without
  // blocking the initial render.
  const fresh = await api()[cfg.api.syncLibrary](false);
  if (fresh && state.categories[state.catIndex].id === cat.id) {
    if (fresh.entries && fresh.entries.length) {
      state.gameLibraryFull[cat.id] = fresh.entries;
      const freshFiltered = applyGameFilter(cat.id, fresh.entries);
      state.items = freshFiltered.length ? freshFiltered : [{ __empty: true, message: `No games match this filter yet` }];
    } else if (fresh.error === "not_logged_in") {
      state.gameLibraryFull[cat.id] = [];
      state.items = [{
        __empty: true,
        message: "No Playnite library export found yet \u2014 install the MeridianExporter Playnite extension, sync your library in Playnite, then check the connection in Settings.",
      }];
    } else {
      state.gameLibraryFull[cat.id] = [];
      state.items = [{ __empty: true, message: `No ${cfg.label} games found in your Playnite library yet.` }];
    }
    state.selected = Math.min(state.selected, state.items.length - 1);
    renderGameFilterSidebar(cat);
    renderItemList(cat);
  }
}

async function storeLoginFlow(storeId) {
  const cfg = STORE_CONFIG[storeId];
  showToast(cfg.loginStartMessage ? cfg.loginStartMessage() : `Sign in to ${cfg.label} in the window that opens\u2026`);
  const result = await api()[cfg.api.login]();
  if (result && result.success) {
    showToast(`Signed in to ${cfg.label}`);
    state.settings = await api().get_settings(); // don't trust the cached pre-login snapshot
    await refreshItemPanel();
  } else {
    showToast(`${cfg.label} sign-in didn't complete` + (result && result.error ? `: ${result.error}` : ""));
  }
}

function formatPlaytime(minutes) {
  if (!minutes) return "Not played yet";
  const hours = minutes / 60;
  return hours >= 1 ? `${hours.toFixed(hours < 10 ? 1 : 0)} hrs played` : `${minutes} min played`;
}

function rowContentFor(cat, item, i) {
  if (item.__browsingEmpty) {
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">This folder is empty</div></div>`;
  }
  if (item.__empty) {
    const msg = item.message || "Nothing added yet — press confirm to add it in Settings";
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">${escapeHtml(msg)}</div></div>`;
  }
  if (item.__storeLogin) {
    const cfg = STORE_CONFIG[item.__store];
    return `
      <div class="tile-title">${cfg.loginButtonLabel || `Sign in with ${cfg.label}`}</div>
      <div class="tile-meta"><span style="font-size:12px;color:var(--text-lo);">${cfg.loginSubtext || "Press confirm to log in and import your library"}</span></div>`;
  }
  if (cat.kind === "game_grid") {
    const cfg = storeConfigFor(cat);
    // item.art is already a ready-to-use URL (http, or the app's own local
    // media server for local files) by the time it reaches the frontend —
    // see main.py's _entries_with_media_urls. Raw file:// paths aren't
    // reliable in this webview backend, so the backend never sends one.
    const artHtml = item.art ? `<img src="${item.art}" alt="" data-fallback-icon>` : iconFor(cat.id);
    return `
      <div class="tile-art${item.hidden ? " tile-art-hidden" : ""}">${artHtml}</div>
      <div class="tile-title">${escapeHtml(item.title)}${item.hidden ? ' <span class="hidden-badge">hidden</span>' : ""}</div>
      <div class="tile-meta">
        <span class="channel-badge ${item.installed ? "installed" : "not-installed"}">${item.installed ? "Installed" : "Not installed"}</span>
        <button class="channel-action" data-store-secondary="${escapeHtml(item.id)}">
          ${item.installed ? cfg.uninstallLabel : cfg.installLabel}
        </button>
      </div>`;
  }
  if (cat.id === "music") {
    return `
      <span class="idx">${String(i + 1).padStart(2, "0")}</span>
      <div class="row-visual">${item.thumbUrl ? `<img src="${item.thumbUrl}" alt="">` : ICONS.music}</div>
      <div class="meta"><div class="title">${escapeHtml(item.title)}</div><div class="subtitle">${escapeHtml(item.artist)} &middot; ${escapeHtml(item.album)}</div></div>
      <span class="dur">${item.durationLabel || ""}</span>`;
  }
  if (cat.kind === "media") { // photos / videos
    return `
      <div class="row-visual">${item.thumbUrl ? `<img src="${item.thumbUrl}" alt="">` : ICONS[cat.id]}</div>
      <div class="meta"><div class="title">${escapeHtml(item.title)}</div></div>
      ${cat.id === "videos" && item.durationLabel ? `<span class="dur">${item.durationLabel}</span>` : ""}`;
  }
  if (cat.kind === "exe_list") {
    const iconHtml = item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : iconFor(cat.id);
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
  }
  if (cat.kind === "macro_list") {
    const iconHtml = item.type === "builtin" ? ICONS.macros : (item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : ICONS.bat);
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
  }
  if (cat.kind === "system_list" || cat.kind === "file_list") {
    return `<div class="row-visual">${ICONS[item.icon]}</div><div class="meta"><div class="title">${escapeHtml(item.label)}</div></div>`;
  }
  return "";
}

function getDisplayType(storeId) {
  const map = (state.settings && state.settings.display_type) || {};
  return map[storeId] || "gallery"; // games default to gallery, matching how this app has always looked
}

function renderItemList(cat) {
  const isGrid = cat.kind === "game_grid" && getDisplayType(cat.store || cat.id) === "gallery";
  const wrap = document.createElement("div");
  wrap.className = isGrid ? "channel-grid" : "item-list";
  if (isGrid) wrap.style.setProperty("--games-per-row", (state.settings && state.settings.games_per_row) || 5);
  state.items.forEach((item, i) => {
    const row = document.createElement("div");
    const isEmpty = !!item.__empty || !!item.__browsingEmpty || !!item.__storeLogin;
    const listHasFocus = !(isGrid && state.gridFocus === "filter");
    if (isGrid) {
      row.className = "channel-tile" + (isEmpty ? " full-width" : "") + (i === state.selected && listHasFocus ? " selected" : "");
    } else {
      row.className = "item-row" + (i === state.selected ? " selected" : "") + (isEmpty ? " empty-prompt-row" : "");
    }
    row.innerHTML = rowContentFor(cat, item, i);
    row.addEventListener("click", () => { state.selected = i; renderItemList(cat); activateCurrentSelection(); });
    const secondaryBtn = row.querySelector("[data-store-secondary]");
    if (secondaryBtn) {
      secondaryBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        state.selected = i;
        activateGameGridSecondary(cat, item);
      });
    }
    row.querySelectorAll("img[data-fallback-icon]").forEach((img) => {
      img.addEventListener("error", () => { img.outerHTML = iconFor(cat.id); }, { once: true });
    });
    wrap.appendChild(row);
  });
  el("item-panel").innerHTML = "";
  el("item-panel").classList.toggle("wide", isGrid);
  el("item-panel").appendChild(wrap);
  const activeEl = wrap.querySelector(".selected");
  if (activeEl && typeof activeEl.scrollIntoView === "function") activeEl.scrollIntoView({ block: "nearest" });
  updatePreviewPane();
  alignCategoryRowToList();
}

// ---------------- activating whatever is currently selected ----------------

async function activateGameGridSecondary(cat, item) {
  const cfg = storeConfigFor(cat);
  playChime();
  if (item.installed) {
    // Labeled "Play Game" now, so it should actually launch — same action
    // as clicking the tile itself, just also reachable as its own explicit
    // button. (Uninstalling isn't exposed here anymore; do that from
    // Playnite directly.)
    await api()[cfg.api.launch](item.id);
    showToast(cfg.uninstallingText(item.title));
  } else {
    await api()[cfg.api.install](item.id);
    showToast(cfg.installingText(item.title));
  }
  setTimeout(() => { api()[cfg.api.syncLibrary](true).then(() => refreshItemPanel()); }, 4000);
}

async function activateCurrentSelection() {
  if (state.radialFocus === "sections") { commitBrowsedSection(); return; }
  const cat = state.categories[state.catIndex];
  if (cat.kind === "direct") {
    const res = await api().open_web();
    if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
    return;
  }
  if (cat.kind === "settings") return; // settings is mouse/click driven, not a linear list

  const item = state.items[state.selected];
  if (!item) return;
  if (item.__browsingEmpty) return; // just an inert "this folder is empty" placeholder
  if (item.__storeLogin) { await storeLoginFlow(item.__store); return; }
  if (item.__empty) { await goToSettingsFor(cat); return; }

  if (cat.id === "music") playMusicAt(state.selected);
  else if (cat.id === "photos") openPhoto(state.selected);
  else if (cat.id === "videos") openVideo(state.selected);
  else if (cat.kind === "exe_list") launchAndNotify(item.path);
  else if (cat.kind === "macro_list") activateMacro(item);
  else if (cat.kind === "system_list") activateSystemItem(item);
  else if (cat.kind === "file_list") activateFileItem(item);
  else if (cat.kind === "game_grid") {
    const cfg = storeConfigFor(cat);
    playChime();
    if (item.installed) { await api()[cfg.api.launch](item.id); }
    else { await api()[cfg.api.install](item.id); showToast(cfg.installingText(item.title)); }
  }
}

// Jump straight into Settings, scrolled to and briefly highlighting the
// block for the section the user just tried to use (since it has nothing
// in it yet). Only triggered by an explicit confirm on the empty-prompt row.
async function goToSettingsFor(cat) {
  const settingsIndex = state.categories.findIndex((c) => c.kind === "settings");
  if (settingsIndex === -1) return;
  state.catIndex = settingsIndex;
  state.selected = 0;
  applyAccent();
  renderCategories();
  await refreshItemPanel();
  try {
    const target = el(`settings-block-${cat.id}`);
    if (target && typeof target.scrollIntoView === "function") target.scrollIntoView({ behavior: "smooth", block: "start" });
    if (target) {
      target.classList.add("settings-block-highlight");
      setTimeout(() => target.classList.remove("settings-block-highlight"), 1600);
    }
  } catch (err) {
    console.warn("Couldn't scroll/highlight the settings block (non-fatal):", err);
  }
  showToast(`Nothing in ${cat.label} yet — add some here.`);
}

// ---------------- launching / macros / system / files ----------------

async function launchAndNotify(path) {
  const res = await api().launch_exe(path);
  if (!res.ok) showToast(`Couldn't launch: ${res.error}`);
}

function showToast(msg) {
  const t = el("empty-toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => t.classList.add("hidden"), 3500);
}

async function activateMacro(item) {
  if (item.type === "builtin") {
    const res = await api().run_macro(item.id);
    showToast(res.ok ? `Closed ${res.closed.length} other program(s).` : `Macro failed: ${res.error}`);
  } else {
    launchAndNotify(item.path);
  }
}

async function activateFileItem(item) {
  const res = item.id === "meridian_explorer" ? await api().launch_meridian_explorer() : await api().open_files();
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
}

async function activateSystemItem(item) {
  const map = {
    shutdown: () => api().system_shutdown(),
    sleep: () => api().system_sleep(),
    hibernate: () => api().system_hibernate(),
    close: () => api().quit_app(),
    controlpanel: () => api().system_control_panel(),
    taskmanager: () => api().system_task_manager(),
    recyclebin: () => api().system_recycle_bin(),
    uninstallapps: () => api().system_uninstall_apps(),
    wifi: () => { openNetworkOverlay("wifi"); return null; },
    bluetooth: () => { openNetworkOverlay("bluetooth"); return null; },
  };
  const fn = map[item.id];
  if (!fn) return;
  const res = await fn();
  if (res && res.ok === false) showToast(`Couldn't complete: ${res.error}`);
}

// ---------------- Wi-Fi / Bluetooth ----------------

let networkMode = "wifi";
let pendingWifiSsid = null;

function closeNetworkOverlay() { el("network-overlay").classList.add("hidden"); }
el("network-close").addEventListener("click", closeNetworkOverlay);
el("network-refresh").addEventListener("click", refreshNetworkList);

async function openNetworkOverlay(mode) {
  networkMode = mode;
  el("network-title").textContent = mode === "wifi" ? "Wi-Fi" : "Bluetooth";
  el("network-overlay").classList.remove("hidden");
  await refreshNetworkList();
}

async function refreshNetworkList() {
  const list = el("network-list");
  list.innerHTML = `<div class="empty-msg">Scanning&hellip;</div>`;
  if (networkMode === "wifi") {
    const res = await api().wifi_scan();
    if (!res.ok) { list.innerHTML = `<div class="empty-msg">${escapeHtml(res.error || "Couldn't scan for networks.")}</div>`; return; }
    renderWifiList(res.networks);
  } else {
    const res = await api().bluetooth_list_devices();
    list.innerHTML = "";
    if (!res.ok) {
      const msg = document.createElement("div");
      msg.className = "empty-msg";
      msg.textContent = res.error || "Couldn't list Bluetooth devices.";
      list.appendChild(msg);
    } else {
      renderBluetoothList(res.devices || []);
    }
    const openBtn = document.createElement("button");
    openBtn.className = "btn-outline";
    openBtn.style.marginTop = "10px";
    openBtn.textContent = "Open Windows Bluetooth settings (to pair a new device)";
    openBtn.addEventListener("click", () => api().open_bluetooth_settings());
    list.appendChild(openBtn);
  }
}

function renderWifiList(networks) {
  const list = el("network-list");
  list.innerHTML = "";
  if (!networks.length) { list.innerHTML = `<div class="empty-msg">No networks found.</div>`; return; }
  networks.forEach((n) => {
    const row = document.createElement("div");
    row.className = "network-row";
    row.innerHTML = `
      ${ICONS.wifi.replace('class="', 'class="net-icon ')}
      <span class="net-name">${escapeHtml(n.ssid)}${n.secured ? " &#128274;" : ""}</span>
      <span class="net-status">${n.connected ? "Connected" : `${n.signal}%`}</span>`;
    const btn = document.createElement("button");
    btn.textContent = n.connected ? "Disconnect" : "Connect";
    btn.addEventListener("click", async () => {
      if (n.connected) {
        const res = await api().wifi_disconnect();
        if (!res.ok) showToast(`Couldn't disconnect: ${res.error}`); else refreshNetworkList();
      } else if (n.secured) {
        openWifiPasswordModal(n.ssid);
      } else {
        const res = await api().wifi_connect(n.ssid, "");
        showToast(res.ok ? `Connected to ${n.ssid}.` : `Couldn't connect: ${res.error}`);
        if (res.ok) refreshNetworkList();
      }
    });
    row.appendChild(btn);
    list.appendChild(row);
  });
}

function renderBluetoothList(devices) {
  const list = el("network-list");
  if (!devices.length) {
    const msg = document.createElement("div");
    msg.className = "empty-msg";
    msg.textContent = "No known Bluetooth devices yet. Pair a new one from Windows settings below.";
    list.appendChild(msg);
    return;
  }
  devices.forEach((d) => {
    const row = document.createElement("div");
    row.className = "network-row";
    row.innerHTML = `
      ${ICONS.bluetooth.replace('class="', 'class="net-icon ')}
      <span class="net-name">${escapeHtml(d.name)}</span>
      <span class="net-status">${d.connected ? "Connected" : "Off"}</span>`;
    const btn = document.createElement("button");
    btn.textContent = d.connected ? "Disconnect" : "Connect";
    btn.addEventListener("click", async () => {
      const res = d.connected ? await api().bluetooth_disconnect(d.id) : await api().bluetooth_connect(d.id);
      showToast(res.ok ? "Done." : `Couldn't complete: ${res.error}`);
      if (res.ok) refreshNetworkList();
    });
    row.appendChild(btn);
    list.appendChild(row);
  });
}

function openWifiPasswordModal(ssid) {
  pendingWifiSsid = ssid;
  el("wifi-password-title").textContent = `Password for ${ssid}`;
  el("wifi-password-input").value = "";
  el("wifi-password-overlay").classList.remove("hidden");
  el("wifi-password-input").focus();
}
function closeWifiPasswordModal() {
  el("wifi-password-overlay").classList.add("hidden");
  pendingWifiSsid = null;
}
el("wifi-password-cancel").addEventListener("click", closeWifiPasswordModal);
el("wifi-password-confirm").addEventListener("click", async () => {
  const password = el("wifi-password-input").value;
  const ssid = pendingWifiSsid;
  closeWifiPasswordModal();
  const res = await api().wifi_connect(ssid, password);
  showToast(res.ok ? `Connected to ${ssid}.` : `Couldn't connect: ${res.error}`);
  if (res.ok) refreshNetworkList();
});
el("wifi-password-input").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Enter") el("wifi-password-confirm").click();
  if (e.key === "Escape") closeWifiPasswordModal();
});

// ---------------- settings ----------------

function buildToggleBlock(title, isOn, onChange, note) {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.innerHTML = `<h3>${escapeHtml(title)}</h3>`;
  const row = document.createElement("div");
  row.className = "settings-row";
  const toggle = document.createElement("div");
  toggle.className = "toggle-switch" + (isOn ? " on" : "");
  toggle.innerHTML = `<div class="knob"></div>`;
  toggle.addEventListener("click", onChange);
  row.appendChild(toggle);
  row.appendChild(document.createTextNode(note || (isOn ? "Enabled" : "Disabled")));
  block.appendChild(row);
  return block;
}

async function renderSettings() {
  const settings = await api().get_settings();
  state.settings = settings;
  applyLayoutClass();
  const panel = el("item-panel");
  panel.innerHTML = "";
  panel.classList.remove("wide");
  const c = document.createElement("div");

  // controller controls quick reference — always the first settings block
  const controlsBlock = document.createElement("div");
  controlsBlock.className = "settings-block";
  controlsBlock.innerHTML = `<h3>Controller controls</h3>
    <p class="settings-note">What each controller button does in Meridian Game Library. Confirm/Back/directions can be remapped in controller_controls.json; combos always use the physical buttons listed. Keyboard: Enter confirm, Space back, arrow keys navigate, the \\ key opens the side panel, Tab opens the Start menu, Escape quits.</p>
    <div class="controls-grid"><div class="controls-row"><span class="controls-btn">A</span><span class="controls-desc">Confirm / launch the selected game</span></div><div class="controls-row"><span class="controls-btn">B</span><span class="controls-desc">Back / close menus and overlays</span></div><div class="controls-row"><span class="controls-btn">D-pad / Left stick</span><span class="controls-desc">Navigate — up/down through games, left/right across sections</span></div><div class="controls-row"><span class="controls-btn">Y (tap)</span><span class="controls-desc">Jump to the Show filter side panel (All / Installed / Not Installed)</span></div><div class="controls-row"><span class="controls-btn">Start</span><span class="controls-desc">Open the Start menu — hide/unhide games, rename titles, show hidden games, close the program</span></div><div class="controls-row"><span class="controls-btn">Start + Back (together)</span><span class="controls-desc">Bring Meridian Game Library to the foreground</span></div><div class="controls-row"><span class="controls-btn">L3 + R3 (click both sticks)</span><span class="controls-desc">Quit the app instantly</span></div></div>`;
  c.appendChild(controlsBlock);

  // One shared connection now — Playnite itself. Steam/GOG/Epic/Luna are
  // just filtered views into whatever Playnite's library export contains.
  c.appendChild(buildPlayniteConnectionBlock(settings));

  // window mode
  const winBlock = document.createElement("div");
  winBlock.className = "settings-block";
  winBlock.innerHTML = `<h3>Window mode</h3>`;
  const radioWrap = document.createElement("div");
  radioWrap.className = "radio-group";
  ["fullscreen", "windowed"].forEach((mode) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + (settings.window_mode === mode ? " active" : "");
    pill.textContent = mode[0].toUpperCase() + mode.slice(1);
    pill.addEventListener("click", async () => { await api().set_window_mode(mode); renderSettings(); });
    radioWrap.appendChild(pill);
  });
  winBlock.appendChild(radioWrap);
  c.appendChild(winBlock);

  // layout mode
  const layoutBlock = document.createElement("div");
  layoutBlock.className = "settings-block";
  layoutBlock.innerHTML = `<h3>Layouts</h3>`;
  const layoutRadioWrap = document.createElement("div");
  layoutRadioWrap.className = "radio-group";
  [["dawning_horizon", "DawningHorizon"], ["night_horizon", "Verticular Blobs"], ["cyber_radial", "CyberRadial"]].forEach(([mode, label]) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + ((settings.layout || "dawning_horizon") === mode ? " active" : "");
    pill.textContent = label;
    pill.addEventListener("click", async () => { await api().set_layout(mode); renderSettings(); });
    layoutRadioWrap.appendChild(pill);
  });
  layoutBlock.appendChild(layoutRadioWrap);
  c.appendChild(layoutBlock);

  // Dawning Horizon primary theme color
  const themeBlock = document.createElement("div");
  themeBlock.className = "settings-block";
  themeBlock.innerHTML = `<h3>Dawning Horizon theme color</h3>`;
  const themeNote = document.createElement("p");
  themeNote.className = "settings-note";
  themeNote.textContent = "Re-tints the DawningHorizon background to a chosen hue; section colors follow as a complementary ROYGBIV rainbow. Only affects the DawningHorizon layout.";
  themeBlock.appendChild(themeNote);
  const currentThemeColor = settings.dawning_theme_color || "original";
  const pickThemeColor = async (value) => {
    await api().set_dawning_theme_color(value);
    state.settings = await api().get_settings();
    applyDawningThemeColor(state.settings);
    renderSettings();
  };
  const origWrap = document.createElement("div");
  origWrap.className = "radio-group";
  const origPill = document.createElement("div");
  origPill.className = "radio-pill" + (currentThemeColor === "original" ? " active" : "");
  origPill.textContent = "Original";
  origPill.addEventListener("click", () => pickThemeColor("original"));
  origWrap.appendChild(origPill);
  themeBlock.appendChild(origWrap);
  [["light", "Light"], ["dark", "Dark"], ["neon", "Neon"], ["primary", "Primary"], ["pastel", "Pastel"], ["bubblegum", "Bubblegum"]].forEach(([pal, label]) => {
    const row = document.createElement("div");
    row.className = "theme-swatch-row";
    const lab = document.createElement("span");
    lab.className = "theme-swatch-label";
    lab.textContent = label;
    row.appendChild(lab);
    DAWNING_HUES.forEach(([hueName, hueDeg]) => {
      const value = `${pal}:${hueName}`;
      const sw = document.createElement("button");
      sw.type = "button";
      sw.className = "theme-swatch" + (currentThemeColor === value ? " active" : "");
      const rec = DAWNING_PALETTES[pal];
      sw.style.background = `hsl(${hueDeg}, ${rec.bg1[0]}%, ${rec.bg1[1]}%)`;
      sw.title = `${label} \u2014 ${hueName}`;
      sw.addEventListener("click", () => pickThemeColor(value));
      row.appendChild(sw);
    });
    themeBlock.appendChild(row);
  });
  c.appendChild(themeBlock);

  // games per row (gallery grid), applies across all layouts/themes
  const perRowBlock = document.createElement("div");
  perRowBlock.className = "settings-block";
  perRowBlock.innerHTML = `<h3>Games Per Row</h3>`;
  const perRowWrap = document.createElement("div");
  perRowWrap.className = "radio-group";
  [3, 4, 5].forEach((n) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + ((settings.games_per_row || 5) === n ? " active" : "");
    pill.textContent = String(n);
    pill.addEventListener("click", async () => { await api().set_games_per_row(n); renderSettings(); if (isGameGridCategory()) refreshItemPanel(); });
    perRowWrap.appendChild(pill);
  });
  perRowBlock.appendChild(perRowWrap);
  c.appendChild(perRowBlock);

  // per-store List Style vs Gallery Style
  Object.entries(STORE_CONFIG).forEach(([storeId, cfg]) => {
    const dtBlock = document.createElement("div");
    dtBlock.className = "settings-block";
    dtBlock.innerHTML = `<h3>${cfg.label} display</h3>`;
    const dtWrap = document.createElement("div");
    dtWrap.className = "radio-group";
    [["gallery", "Gallery Style"], ["list", "List Style"]].forEach(([type, label]) => {
      const pill = document.createElement("div");
      pill.className = "radio-pill" + (getDisplayType(storeId) === type ? " active" : "");
      pill.textContent = label;
      pill.addEventListener("click", async () => { await api().set_display_type(storeId, type); renderSettings(); });
      dtWrap.appendChild(pill);
    });
    dtBlock.appendChild(dtWrap);
    c.appendChild(dtBlock);
  });

  // game library import source — Playnite or Heroic, never both
  const importBlock = document.createElement("div");
  importBlock.className = "settings-block";
  importBlock.innerHTML = `<h3>Import titles from</h3>`;
  const importRadioWrap = document.createElement("div");
  importRadioWrap.className = "radio-group";
  [["playnite", "Playnite"], ["heroic", "Heroic Games Launcher"]].forEach(([source, label]) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + ((settings.game_import_source || "playnite") === source ? " active" : "");
    pill.textContent = label;
    pill.addEventListener("click", async () => {
      await api().set_game_import_source(source);
      await refreshAfterSettingsChange();
    });
    importRadioWrap.appendChild(pill);
  });
  importBlock.appendChild(importRadioWrap);
  const importNote = document.createElement("p");
  importNote.className = "settings-note";
  importNote.textContent = settings.game_import_source === "heroic"
    ? "Reading your Epic/GOG/sideloaded library from Heroic Games Launcher. Steam and Luna aren't something Heroic manages, so those sections will show as not connected."
    : "Reading your library from Playnite (via the MeridianExporter extension). Switch to Heroic Games Launcher above if that's what you use instead.";
  importBlock.appendChild(importNote);
  c.appendChild(importBlock);

  // Playnite filter-preset sections
  const pfBlock = buildToggleBlock(
    "Playnite filter sections",
    settings.playnite_filter_sections,
    async () => {
      await api().set_playnite_filter_sections(!settings.playnite_filter_sections);
      await refreshAfterSettingsChange();
    },
    settings.playnite_filter_sections
      ? `Your saved Playnite filter presets show as their own sections${state.filterPresets && state.filterPresets.length ? ` (${state.filterPresets.length} found)` : " (none found yet \u2014 re-run the Meridian export in Playnite after updating the extension)"}.`
      : "Off \u2014 turn on to pull your saved Playnite filter presets in as similarly named sections.",
  );
  c.appendChild(pfBlock);

  // battery indicator
  c.appendChild(buildToggleBlock(
    "Battery Level Indicator",
    settings.battery_indicator,
    async () => { await api().set_battery_indicator(!settings.battery_indicator); renderSettings(); updateBatteryIndicator(); },
  ));

  // background image
  const bgBlock = document.createElement("div");
  bgBlock.className = "settings-block";
  bgBlock.innerHTML = `<h3>Custom background</h3>`;
  const bgBtn = document.createElement("button");
  bgBtn.className = "btn-outline";
  bgBtn.textContent = settings.background_image ? "Change image" : "Choose image";
  bgBtn.addEventListener("click", async () => { await api().set_background(); applyBackground(await api().get_settings()); renderSettings(); });
  bgBlock.appendChild(bgBtn);
  if (settings.background_image) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_background(); applyBackground(await api().get_settings()); renderSettings(); });
    bgBlock.appendChild(clear);
  }
  c.appendChild(bgBlock);

  // overlay
  const ovBlock = document.createElement("div");
  ovBlock.className = "settings-block";
  ovBlock.innerHTML = `<h3>Custom overlay</h3>`;
  const ovRow = document.createElement("div");
  ovRow.className = "settings-row";
  const toggle = document.createElement("div");
  toggle.className = "toggle-switch" + (settings.overlay_enabled ? " on" : "");
  toggle.innerHTML = `<div class="knob"></div>`;
  toggle.addEventListener("click", async () => {
    await api().set_overlay_enabled(!settings.overlay_enabled);
    await applyOverlay(await api().get_settings());
    renderSettings();
  });
  ovRow.appendChild(toggle);
  ovRow.appendChild(document.createTextNode("Enabled (white becomes transparent)"));
  ovBlock.appendChild(ovRow);
  const ovBtn = document.createElement("button");
  ovBtn.className = "btn-outline";
  ovBtn.textContent = settings.overlay_image ? "Change overlay.png" : "Choose overlay image";
  ovBtn.addEventListener("click", async () => { await api().set_overlay(); await applyOverlay(await api().get_settings()); renderSettings(); });
  ovBlock.appendChild(ovBtn);
  if (settings.overlay_image) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_overlay(); await applyOverlay(await api().get_settings()); renderSettings(); });
    ovBlock.appendChild(clear);
  }
  c.appendChild(ovBlock);

  // app data folder (settings.json, controls files, cached thumbnails)
  const dataBlock = document.createElement("div");
  dataBlock.className = "settings-block";
  dataBlock.innerHTML = `<h3>App data folder</h3>`;
  const dataBtn = document.createElement("button");
  dataBtn.className = "btn-outline";
  dataBtn.textContent = "Open App data folder";
  dataBtn.addEventListener("click", async () => {
    const result = await api().open_app_data_folder();
    if (!result || result.ok === false) {
      showToast(result && result.error ? result.error : "Couldn't open the app data folder.");
    }
  });
  dataBlock.appendChild(dataBtn);
  c.appendChild(dataBlock);


  // credit footer — always the very last thing in the settings box
  const creditBlock = document.createElement("div");
  creditBlock.className = "settings-block settings-credit";
  creditBlock.innerHTML = `<p>Vibecoded by Samuel "Zenith" Schimmel (Madisico) 2026; This is open source software. Donations Appreciated, but Money Not Required.</p>`;
  c.appendChild(creditBlock);

  panel.appendChild(c);
  alignCategoryRowToList();
}

function buildPlayniteConnectionBlock(settings) {
  const cfg = settings.playnite || {};
  const block = document.createElement("div");
  block.className = "settings-block";
  block.innerHTML = `<h3>Playnite connection</h3>`;

  const status = document.createElement("div");
  status.className = "settings-row";
  status.textContent = cfg.export_available
    ? "Connected \u2014 reading your Playnite library export"
    : "Not connected yet";
  block.appendChild(status);

  const note = document.createElement("div");
  note.className = "settings-row";
  note.style.fontSize = "12px";
  note.style.color = "var(--text-lo)";
  note.textContent = "Steam, GOG, Epic, and Luna all read from the same Playnite library export \u2014 install the MeridianExporter Playnite extension, sync your library there, then point this at the exported file:";
  block.appendChild(note);

  const pathRow = document.createElement("div");
  pathRow.className = "settings-row";
  const pathLabel = document.createElement("span");
  pathLabel.textContent = cfg.export_path || "Using the default location";
  pathLabel.style.fontSize = "12px";
  pathLabel.style.overflow = "hidden";
  pathLabel.style.textOverflow = "ellipsis";
  pathLabel.style.whiteSpace = "nowrap";
  pathLabel.style.flex = "1";
  const browseBtn = document.createElement("button");
  browseBtn.className = "btn-outline";
  browseBtn.textContent = "Browse\u2026";
  browseBtn.addEventListener("click", async () => {
    const path = await api().playnite_pick_export_file();
    if (path) { await api().playnite_set_export_path(path); renderSettings(); }
  });
  pathRow.appendChild(pathLabel);
  pathRow.appendChild(browseBtn);
  block.appendChild(pathRow);

  const btnRow = document.createElement("div");
  btnRow.className = "settings-row";
  const checkBtn = document.createElement("button");
  checkBtn.className = "btn-outline";
  checkBtn.textContent = "Check connection";
  checkBtn.addEventListener("click", async () => {
    showToast("Checking for a Playnite library export\u2026");
    const result = await api().playnite_status();
    if (result.available) {
      const s = result.summary || {};
      showToast(`Connected \u2014 ${s.total || 0} games found (Steam ${s.steam || 0}, GOG ${s.gog || 0}, Epic ${s.epic || 0}, Luna ${s.amazon || 0}, Other ${s.other || 0})`);
    } else {
      showToast("Still not connected \u2014 check the export path and that the Playnite extension has run at least once");
    }
    renderSettings();
  });
  btnRow.appendChild(checkBtn);

  const syncBtn = document.createElement("button");
  syncBtn.className = "btn-outline";
  syncBtn.textContent = "Sync with Playnite now";
  syncBtn.addEventListener("click", async () => {
    showToast("Opening Playnite in the background to sync\u2026 this can take up to a minute");
    const result = await api().playnite_sync_now();
    showToast(result.synced ? "Synced \u2014 library updated" : "Didn't finish in time \u2014 open Playnite normally once to check for anything blocking it");
    renderSettings();
    if (isGameGridCategory()) refreshItemPanel();
  });
  btnRow.appendChild(syncBtn);
  block.appendChild(btnRow);

  return block;
}

function buildExeSectionBlock(sec) {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.id = `settings-block-${sec.id}`;
  const h = document.createElement("h3");
  h.textContent = sec.label;
  block.appendChild(h);
  const listWrap = document.createElement("div");
  block.appendChild(listWrap);

  const refreshList = (items) => {
    listWrap.innerHTML = "";
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(it.name)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => {
        const updated = await api().remove_exe_from_section(sec.id, it.path);
        refreshList(updated);
      });
      listWrap.appendChild(row);
    });
  };

  api().list_section_items(sec.id).then(refreshList);

  const addBtn = document.createElement("button");
  addBtn.className = "add-folder-btn";
  addBtn.textContent = `+ Add .exe to ${sec.label}`;
  addBtn.addEventListener("click", async () => {
    const updated = await api().add_exe_to_section(sec.id);
    refreshList(updated);
  });
  block.appendChild(addBtn);

  if (sec.custom) {
    const rm = document.createElement("button");
    rm.className = "btn-link";
    rm.textContent = "Remove this section";
    rm.addEventListener("click", async () => { await api().remove_custom_section(sec.id); await refreshAfterSettingsChange(); });
    block.appendChild(rm);
  }

  return block;
}

async function buildMacroSectionBlock() {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.id = "settings-block-macros";
  block.innerHTML = `<h3>Macros</h3>`;
  const listWrap = document.createElement("div");
  block.appendChild(listWrap);

  const refreshList = (items) => {
    listWrap.innerHTML = "";
    items.filter((it) => it.type !== "builtin").forEach((it) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(it.name)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => {
        const updated = await api().remove_macro_item(it.path);
        refreshList(updated);
      });
      listWrap.appendChild(row);
    });
  };

  const items = await api().list_macro_items();
  refreshList(items);

  const addBtn = document.createElement("button");
  addBtn.className = "add-folder-btn";
  addBtn.textContent = "+ Add .bat to Macros";
  addBtn.addEventListener("click", async () => {
    const updated = await api().add_bat_to_macros();
    refreshList(updated);
  });
  block.appendChild(addBtn);
  return block;
}

async function refreshAfterSettingsChange() {
  const settings = await api().get_settings();
  state.settings = settings;
  await loadFilterPresets(settings);
  state.categories = buildCategories(settings);
  if (state.catIndex >= state.categories.length) state.catIndex = state.categories.length - 1;
  renderCategories();
  await renderSettings();
}

// ---------------- custom section modal ----------------

function openSectionModal() {
  el("modal-overlay").classList.remove("hidden");
  el("modal-input").value = "";
  el("modal-input").focus();
}
function closeSectionModal() {
  el("modal-overlay").classList.add("hidden");
}
el("modal-cancel").addEventListener("click", closeSectionModal);
el("modal-confirm").addEventListener("click", async () => {
  const name = el("modal-input").value.trim();
  if (!name) return;
  await api().add_custom_section(name);
  closeSectionModal();
  await refreshAfterSettingsChange();
});
el("modal-input").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Enter") el("modal-confirm").click();
  if (e.key === "Escape") closeSectionModal();
});

// ---------------- appearance: background & overlay ----------------

function applyBackground(settings) {
  const layer = el("bg-image-layer");
  if (settings.background_image) {
    api().get_media_url(settings.background_image).then((url) => {
      layer.style.backgroundImage = `url("${url}")`;
    });
  } else {
    layer.style.backgroundImage = "none";
  }
}

async function applyOverlay(settings) {
  const canvas = el("overlay-canvas");
  if (!settings.overlay_enabled || !settings.overlay_image) {
    canvas.classList.remove("active");
    return;
  }
  const url = await api().get_media_url(settings.overlay_image);
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    drawOverlay(img);
    canvas.classList.add("active");
  };
  img.src = url;
  applyOverlay._img = img; // keep alive, redraw on resize
}

function drawOverlay(img) {
  const canvas = el("overlay-canvas");
  const w = window.innerWidth, h = window.innerHeight;
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, w, h);

  const scale = Math.max(w / img.width, h / img.height);
  const dw = img.width * scale, dh = img.height * scale;
  const dx = (w - dw) / 2, dy = (h - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);

  const data = ctx.getImageData(0, 0, w, h);
  const px = data.data;
  const THRESH = 235;
  for (let i = 0; i < px.length; i += 4) {
    if (px[i] > THRESH && px[i + 1] > THRESH && px[i + 2] > THRESH) {
      px[i + 3] = 0;
    }
  }
  ctx.putImageData(data, 0, 0);
}

window.addEventListener("resize", () => {
  if (applyOverlay._img) drawOverlay(applyOverlay._img);
});

// ---------------- music playback ----------------

const audioEl = () => el("audio-el");

function playMusicAt(i) {
  const item = state.items[i];
  if (!item) return;
  state.playIndex = i;
  audioEl().src = item.url;
  audioEl().play();
  el("now-playing").classList.remove("hidden");
  el("np-title").textContent = item.title;
  el("np-artist").textContent = item.artist;
  el("np-thumb").src = item.thumbUrl || "";
  renderItemList(state.categories[state.catIndex]);
}
audioEl().addEventListener("timeupdate", () => {
  const a = audioEl();
  if (a.duration) el("np-progress-fill").style.width = `${(a.currentTime / a.duration) * 100}%`;
});
audioEl().addEventListener("ended", () => { if (state.playIndex < state.items.length - 1) playMusicAt(state.playIndex + 1); });
el("np-play").addEventListener("click", () => { const a = audioEl(); a.paused ? a.play() : a.pause(); });
el("np-next").addEventListener("click", () => { if (state.playIndex < state.items.length - 1) playMusicAt(state.playIndex + 1); });
el("np-prev").addEventListener("click", () => { if (state.playIndex > 0) playMusicAt(state.playIndex - 1); });

// ---------------- video / photo overlays ----------------

function openVideo(i) {
  const item = state.items[i];
  const v = el("video-el");
  v.src = item.url;
  v.classList.toggle("video-fullscreen", !!(state.settings && state.settings.video_fullscreen));
  el("video-overlay").classList.remove("hidden");
  v.play();
}
function closeVideo() {
  const v = el("video-el");
  v.pause(); v.removeAttribute("src"); v.load();
  el("video-overlay").classList.add("hidden");
}
el("video-close").addEventListener("click", closeVideo);

// Controller (and equivalent keyboard) playback controls while a video is open.
function handleVideoControllerInput(action) {
  const v = el("video-el");
  if (action === "confirm") { if (v.paused) v.play(); else v.pause(); }
  else if (action === "left") { v.currentTime = Math.max(0, v.currentTime - 10); }
  else if (action === "right") { v.currentTime = Math.min(v.duration || v.currentTime + 10, v.currentTime + 10); }
  else if (action === "up") { v.volume = Math.min(1, v.volume + 0.1); }
  else if (action === "down") { v.volume = Math.max(0, v.volume - 0.1); }
  else if (action === "back") { closeVideo(); }
}

let photoIndex = 0;
function openPhoto(i) { photoIndex = i; showPhoto(); el("photo-overlay").classList.remove("hidden"); }
function showPhoto() { el("photo-el").src = state.items[photoIndex].fullUrl; }
function closePhoto() { el("photo-overlay").classList.add("hidden"); }
el("photo-close").addEventListener("click", closePhoto);
el("photo-prev").addEventListener("click", () => { photoIndex = (photoIndex - 1 + state.items.length) % state.items.length; showPhoto(); });
el("photo-next").addEventListener("click", () => { photoIndex = (photoIndex + 1) % state.items.length; showPhoto(); });

function isOverlayOpen() {
  return !el("video-overlay").classList.contains("hidden")
    || !el("photo-overlay").classList.contains("hidden")
    || !el("modal-overlay").classList.contains("hidden")
    || !el("wifi-password-overlay").classList.contains("hidden")
    || !el("network-overlay").classList.contains("hidden");
}

function handleBack() {
  if (!el("video-overlay").classList.contains("hidden")) { closeVideo(); return; }
  if (!el("photo-overlay").classList.contains("hidden")) { closePhoto(); return; }
  if (!el("modal-overlay").classList.contains("hidden")) { closeSectionModal(); return; }
  if (!el("wifi-password-overlay").classList.contains("hidden")) { closeWifiPasswordModal(); return; }
  if (!el("network-overlay").classList.contains("hidden")) { closeNetworkOverlay(); return; }
  const cat = state.categories[state.catIndex];
  if (cat && cat.kind === "media" && state.settings && state.settings.load_subfolders === false) {
    const stack = state.folderStack[cat.id];
    if (stack && stack.length > 1) { goUpFolder(cat.id); return; }
  }
  if (state.radialFocus !== "sections") {
    if (isGameGridCategory() && state.gridFocus === "filter") {
      state.gridFocus = "list";
      renderGameFilterSidebar(cat);
      return;
    }
    state.radialFocus = "sections";
    state.sectionsBrowseIndex = state.catIndex;
    renderCategories();
    return;
  }
  // Nothing else to "back" out of — the category bar is always visible.
}

// ---------------- on-screen keyboard (controller-navigable) ----------------
// Shown automatically whenever a text/password input is focused, positioned
// below it. Real physical keyboard typing keeps working the whole time —
// see the "bail out for focused inputs" check in the keydown handler below.

const OSK_ROWS = [
  ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
  ["⇧", "z", "x", "c", "v", "b", "n", "m", "⌫"],
  ["space", "done"],
];
let oskShift = false;
let oskRow = 1;
let oskCol = 0;
let oskInputEl = null;

function buildOsk() {
  const container = el("osk");
  container.innerHTML = "";
  OSK_ROWS.forEach((row, r) => {
    const rowEl = document.createElement("div");
    rowEl.className = "osk-row";
    row.forEach((key, c) => {
      const btn = document.createElement("div");
      btn.className = "osk-key" + (key === "space" || key === "done" ? " wide" : "");
      btn.textContent = key === "space" ? "Space" : key === "done" ? "Done" : key;
      btn.dataset.row = String(r);
      btn.dataset.col = String(c);
      btn.addEventListener("mousedown", (e) => e.preventDefault()); // don't steal focus from the real input
      btn.addEventListener("click", () => { oskRow = r; oskCol = c; activateOskKey(); });
      rowEl.appendChild(btn);
    });
    container.appendChild(rowEl);
  });
}

function highlightOskKey() {
  el("osk").querySelectorAll(".osk-key").forEach((btn) => {
    const isSel = Number(btn.dataset.row) === oskRow && Number(btn.dataset.col) === oskCol;
    btn.classList.toggle("osk-selected", isSel);
  });
}

function showOskFor(inputEl) {
  oskInputEl = inputEl;
  oskRow = 1; oskCol = 0;
  const osk = el("osk");
  osk.classList.remove("hidden");
  const rect = inputEl.getBoundingClientRect();
  osk.style.top = `${rect.bottom + 8}px`;
  osk.style.left = `${rect.left}px`;
  highlightOskKey();
}

function hideOsk() {
  el("osk").classList.add("hidden");
  oskInputEl = null;
}

function isOskCapturing() {
  return oskInputEl !== null && !el("osk").classList.contains("hidden");
}

function insertIntoOskInput(text) {
  if (!oskInputEl) return;
  oskInputEl.value += text;
  oskInputEl.dispatchEvent(new Event("input", { bubbles: true }));
}

function activateOskKey() {
  if (!oskInputEl) { highlightOskKey(); return; }
  const key = OSK_ROWS[oskRow][oskCol];
  if (key === "⇧") { oskShift = !oskShift; }
  else if (key === "⌫") { oskInputEl.value = oskInputEl.value.slice(0, -1); oskInputEl.dispatchEvent(new Event("input", { bubbles: true })); }
  else if (key === "space") { insertIntoOskInput(" "); }
  else if (key === "done") { const inp = oskInputEl; hideOsk(); inp.blur(); }
  else { insertIntoOskInput(oskShift ? key.toUpperCase() : key); oskShift = false; }
  highlightOskKey();
}

function handleOskControllerInput(action) {
  const row = OSK_ROWS[oskRow];
  if (action === "left") oskCol = Math.max(0, oskCol - 1);
  else if (action === "right") oskCol = Math.min(row.length - 1, oskCol + 1);
  else if (action === "up") { oskRow = Math.max(0, oskRow - 1); oskCol = Math.min(oskCol, OSK_ROWS[oskRow].length - 1); }
  else if (action === "down") { oskRow = Math.min(OSK_ROWS.length - 1, oskRow + 1); oskCol = Math.min(oskCol, OSK_ROWS[oskRow].length - 1); }
  else if (action === "confirm") { activateOskKey(); return; }
  else if (action === "back") { const inp = oskInputEl; hideOsk(); if (inp) inp.blur(); return; }
  highlightOskKey();
}

document.addEventListener("focusin", (e) => {
  if (e.target.tagName === "INPUT" && (e.target.type === "text" || e.target.type === "password")) {
    showOskFor(e.target);
  }
});
document.addEventListener("focusout", (e) => {
  if (e.target === oskInputEl) {
    setTimeout(() => { if (document.activeElement !== oskInputEl) hideOsk(); }, 120);
  }
});

// ---------------- intro video ----------------

async function playIntroIfConfigured() {
  const settings = state.settings;
  if (!settings.opening_video) { state.introDismissed = true; return; }
  const url = await api().get_media_url(settings.opening_video);
  const v = el("intro-video-el");
  v.src = url;
  el("intro-overlay").classList.remove("hidden");
  v.play().catch(() => {});
  const dismiss = () => {
    if (state.introDismissed) return;
    state.introDismissed = true;
    v.pause();
    el("intro-overlay").classList.add("hidden");
  };
  v.addEventListener("ended", dismiss);
  window.addEventListener("keydown", dismiss, { once: true });
  window.addEventListener("mousedown", dismiss, { once: true });
  window._dismissIntro = dismiss; // reachable from controller bridge
}

// ---------------- keyboard ----------------
// Confirm/Back/Escape are edge-triggered (ignore e.repeat) since they
// trigger discrete one-shot actions (launch, close, shut down, etc).
// Holding a key shouldn't be able to re-fire those — only Up/Down/Left/Right
// (pure browsing) are allowed to auto-repeat.

document.addEventListener("keydown", (e) => {
  if (!state.introDismissed) return; // any key handled by the intro dismiss listener

  // Let real typing through untouched whenever a text/password field has
  // focus — the on-screen keyboard (if visible) is driven by the
  // controller separately and doesn't compete with this.
  const active = document.activeElement;
  if (active && active.tagName === "INPUT" && (active.type === "text" || active.type === "password")) {
    if (e.key === "Escape") { e.preventDefault(); if (!e.repeat) api().quit_app(); }
    return;
  }

  if (e.key === "Escape") {
    e.preventDefault();
    if (!e.repeat) api().quit_app();
    return;
  }

  const kc = state.keyboardControls;
  const mapped = kc && [kc.confirm, kc.back, kc.up, kc.down, kc.left, kc.right].includes(e.key);
  if (mapped) e.preventDefault(); // stop space-bar page scroll / arrow-key div scroll fighting our nav

  if (!el("video-overlay").classList.contains("hidden")) {
    if (kc && e.key === kc.confirm && !e.repeat) handleVideoControllerInput("confirm");
    else if (kc && e.key === kc.left) handleVideoControllerInput("left");
    else if (kc && e.key === kc.right) handleVideoControllerInput("right");
    else if (kc && e.key === kc.up) handleVideoControllerInput("up");
    else if (kc && e.key === kc.down) handleVideoControllerInput("down");
    else if (kc && e.key === kc.back && !e.repeat) handleVideoControllerInput("back");
    return;
  }

  if (isOverlayOpen()) {
    if (e.key === "ArrowLeft" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (e.key === "ArrowRight" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (kc && e.key === kc.back && !e.repeat) handleBack();
    return;
  }

  if (isStartMenuOpen()) {
    if (kc && e.key === kc.up) handleStartMenuInput("up");
    else if (kc && e.key === kc.down) handleStartMenuInput("down");
    else if (kc && e.key === kc.confirm && !e.repeat) handleStartMenuInput("confirm");
    else if ((kc && e.key === kc.back && !e.repeat) || e.key === "Tab") handleStartMenuInput("back");
    if (e.key === "Tab") e.preventDefault();
    return;
  }
  if (e.key === "Tab") { e.preventDefault(); if (!e.repeat) toggleStartMenu(); return; }

  if (!kc) return;
  if (e.key === kc.confirm) { if (!e.repeat) activateCurrentSelection(); }
  else if (e.key === kc.back) { if (!e.repeat) handleBack(); }
  else if (e.key === "\\") { if (!e.repeat) handleJumpToSubfolder(); }
  else if (e.key === kc.up) handleDirectionalUp();
  else if (e.key === kc.down) handleDirectionalDown();
  else if (e.key === kc.left) handleDirectionalLeft();
  else if (e.key === kc.right) handleDirectionalRight();
});


// ---------------- Start menu (controller Start button / Tab key) ----------------
// A contextual quick menu: game-management actions when the selection is a
// game tile, plus global entries. Options are rebuilt every time it opens
// so hidden/unhidden state is always current.

let startMenuState = null; // {options: [{id,label}], index} when open

function isStartMenuOpen() { return startMenuState !== null; }

function currentGameItemForStartMenu() {
  const cat = state.categories[state.catIndex];
  if (!cat || cat.kind !== "game_grid") return null;
  const item = state.items[state.selected];
  if (!item || item.__empty || item.__storeLogin || item.__browsingEmpty || !item.id) return null;
  return { cat, item };
}

function buildStartMenuOptions() {
  const opts = [];
  const sel = currentGameItemForStartMenu();
  if (sel) {
    const { item } = sel;
    if (!item.hidden) opts.push({ id: "hide", label: `Hide "${item.title}"` });
    if (item.hidden) opts.push({ id: "unhide", label: `Unhide "${item.title}"` });
    opts.push({ id: "rename", label: `Rename "${item.title}"` });
  }
  // "Unhide hidden games" normally; flips to "Hide hidden games" only while
  // hidden titles are being shown.
  const showingHidden = !!(state.settings && state.settings.show_hidden_games);
  opts.push({ id: "toggle_hidden", label: showingHidden ? "Hide hidden games" : "Unhide hidden games" });
  opts.push({ id: "close_program", label: "Close program" });
  return opts;
}

function ensureStartMenuDom() {
  if (el("start-menu-overlay")) return;
  const overlay = document.createElement("div");
  overlay.id = "start-menu-overlay";
  overlay.className = "overlay hidden";
  overlay.innerHTML = `
    <div id="start-menu-box">
      <h3 id="start-menu-title">Start</h3>
      <div id="start-menu-list"></div>
      <p id="start-menu-hint">Confirm to select \u00b7 Back or Start to close</p>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeStartMenu(); });
}

function renderStartMenu() {
  const list = el("start-menu-list");
  list.innerHTML = "";
  startMenuState.options.forEach((opt, i) => {
    const row = document.createElement("div");
    row.className = "start-menu-row" + (i === startMenuState.index ? " selected" : "");
    row.textContent = opt.label;
    row.addEventListener("click", () => { startMenuState.index = i; activateStartMenuOption(); });
    list.appendChild(row);
  });
}

function openStartMenu() {
  ensureStartMenuDom();
  startMenuState = { options: buildStartMenuOptions(), index: 0 };
  renderStartMenu();
  el("start-menu-overlay").classList.remove("hidden");
}

function closeStartMenu() {
  startMenuState = null;
  const overlay = el("start-menu-overlay");
  if (overlay) overlay.classList.add("hidden");
}

function toggleStartMenu() {
  if (isStartMenuOpen()) closeStartMenu();
  else openStartMenu();
}

async function activateStartMenuOption() {
  const opt = startMenuState && startMenuState.options[startMenuState.index];
  if (!opt) return;
  const sel = currentGameItemForStartMenu();

  if (opt.id === "hide" && sel) {
    // in-menu confirmation step instead of a separate dialog
    startMenuState = {
      options: [
        { id: "hide_confirm", label: `Yes, hide "${sel.item.title}"` },
        { id: "cancel", label: "Cancel" },
      ],
      index: 0,
    };
    renderStartMenu();
    return;
  }
  if (opt.id === "hide_confirm" && sel) {
    state.settings = await api().set_game_hidden(sel.item.id, true);
    closeStartMenu();
    showToast(`Hidden "${sel.item.title}" \u2014 unhide it any time from the Start menu.`);
    await refreshItemPanel();
    return;
  }
  if (opt.id === "unhide" && sel) {
    state.settings = await api().set_game_hidden(sel.item.id, false);
    closeStartMenu();
    showToast(`"${sel.item.title}" is visible again.`);
    await refreshItemPanel();
    return;
  }
  if (opt.id === "rename" && sel) {
    closeStartMenu();
    openRenameModal(sel.item);
    return;
  }
  if (opt.id === "toggle_hidden") {
    const next = !(state.settings && state.settings.show_hidden_games);
    state.settings = await api().set_show_hidden_games(next);
    closeStartMenu();
    showToast(next ? "Hidden games are now shown (dimmed)." : "Hidden games are hidden again.");
    await refreshItemPanel();
    return;
  }
  if (opt.id === "cancel") {
    startMenuState = { options: buildStartMenuOptions(), index: 0 };
    renderStartMenu();
    return;
  }
  if (opt.id === "close_program") {
    await api().quit_app();
  }
}

function handleStartMenuInput(action) {
  if (!startMenuState) return;
  const n = startMenuState.options.length;
  if (action === "up") startMenuState.index = (startMenuState.index - 1 + n) % n;
  else if (action === "down") startMenuState.index = (startMenuState.index + 1) % n;
  else if (action === "confirm") { activateStartMenuOption(); return; }
  else if (action === "back" || action === "start_menu") { closeStartMenu(); return; }
  renderStartMenu();
}

// ---------------- rename modal (Start menu -> Rename Title) ----------------

let renameTargetItem = null;

function ensureRenameDom() {
  if (el("rename-overlay")) return;
  const overlay = document.createElement("div");
  overlay.id = "rename-overlay";
  overlay.className = "overlay hidden";
  overlay.innerHTML = `
    <div id="modal-box">
      <h3 id="rename-title">Rename title</h3>
      <input id="rename-input" type="text" placeholder="Display name" maxlength="80" />
      <p class="settings-note">Leave empty and save to restore the original title. Only changes how it shows here \u2014 Playnite is untouched.</p>
      <div id="modal-actions">
        <button id="rename-cancel">Cancel</button>
        <button id="rename-confirm">Save</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  el("rename-cancel").addEventListener("click", closeRenameModal);
  el("rename-confirm").addEventListener("click", async () => {
    if (!renameTargetItem) { closeRenameModal(); return; }
    const name = el("rename-input").value.trim();
    state.settings = await api().set_game_rename(renameTargetItem.id, name);
    const target = renameTargetItem;
    closeRenameModal();
    showToast(name ? `Renamed to "${name}".` : "Restored the original title.");
    await refreshItemPanel();
  });
  el("rename-input").addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") el("rename-confirm").click();
    if (e.key === "Escape") closeRenameModal();
  });
}

function openRenameModal(item) {
  ensureRenameDom();
  renameTargetItem = item;
  el("rename-overlay").classList.remove("hidden");
  const input = el("rename-input");
  input.value = item.title || "";
  input.focus(); // focusin handler pops the on-screen keyboard for controller text entry
}

function closeRenameModal() {
  renameTargetItem = null;
  const overlay = el("rename-overlay");
  if (overlay) { overlay.classList.add("hidden"); }
  hideOsk();
}

// ---------------- controller bridge (called from Python via evaluate_js) ----------------
// Note: confirm/back are already edge-triggered on the Python side (XInput
// rising-edge detection), so no repeat-guard is needed here for those.

window.handleControllerInput = function (action) {
  if (!state.introDismissed) return;
  if (isOskCapturing()) { handleOskControllerInput(action); return; }
  if (isStartMenuOpen()) { handleStartMenuInput(action); return; }
  if (el("rename-overlay") && !el("rename-overlay").classList.contains("hidden")) {
    if (action === "back") closeRenameModal();
    return;
  }
  if (action === "start_menu") { toggleStartMenu(); return; }
  if (!el("video-overlay").classList.contains("hidden")) { handleVideoControllerInput(action); return; }
  if (isOverlayOpen()) {
    if (action === "left" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (action === "right" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (action === "back") handleBack();
    return;
  }
  if (action === "confirm") activateCurrentSelection();
  else if (action === "back") handleBack();
  else if (action === "y_subfolder") handleJumpToSubfolder();
  else if (action === "up") handleDirectionalUp();
  else if (action === "down") handleDirectionalDown();
  else if (action === "left") handleDirectionalLeft();
  else if (action === "right") handleDirectionalRight();
};

window.handleControllerAny = function () {
  if (!state.introDismissed && window._dismissIntro) window._dismissIntro();
};

// ---------------- boot ----------------

// ---------------- Verticular Blobs: animated blob background ----------------
// Same system as Meridian Launcher's NightHorizon — see that app.js for the
// fuller comment. Runs behind "Verticular Blobs" (this app's renamed
// night_horizon layout); fades out when CyberRadial is active.
let blobState = null;
function hexToRgbString(hex) {
  const m = hex.trim().replace("#", "");
  const full = m.length === 3 ? m.split("").map((c) => c + c).join("") : m;
  const n = parseInt(full, 16);
  if (Number.isNaN(n)) return "150,255,120";
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
}
function initBlobBackground() {
  if (blobState) return;
  const canvas = document.createElement("canvas");
  canvas.id = "blob-canvas";
  canvas.style.cssText = "position:fixed;inset:0;z-index:0;pointer-events:none;transition:opacity 500ms ease;filter:blur(20px) contrast(34) saturate(1.4);";
  const horizon = el("horizon-glow");
  horizon.insertAdjacentElement("afterend", canvas);
  const ctx = canvas.getContext("2d");

  const BLOB_COUNT = 16;
  const SPEED = 2.4; // 6x the original 0.4
  const blobs = Array.from({ length: BLOB_COUNT }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    vx: (Math.random() - 0.5) * SPEED,
    vy: (Math.random() - 0.5) * SPEED,
    r: 40 + Math.random() * 60,
    shade: 0.75 + Math.random() * 0.5, // per-blob brightness variance around the accent color
    spin: Math.random() * Math.PI * 2,
    spinSpeed: (Math.random() < 0.5 ? -1 : 1) * (0.04 + Math.random() * 0.08),
  }));

  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  function step() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const accentRgb = hexToRgbString(getComputedStyle(document.documentElement).getPropertyValue("--active-accent") || "#a6e83f");

    for (const b of blobs) {
      b.x += b.vx; b.y += b.vy;
      b.spin += b.spinSpeed;
      if (b.x - b.r < 0 || b.x + b.r > w) { b.vx *= -1; b.x = Math.max(b.r, Math.min(w - b.r, b.x)); }
      if (b.y - b.r < 0 || b.y + b.r > h) { b.vy *= -1; b.y = Math.max(b.r, Math.min(h - b.r, b.y)); }
    }

    for (const b of blobs) {
      const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      g.addColorStop(0, `rgba(${accentRgb},${0.9 * b.shade})`);
      g.addColorStop(1, `rgba(${accentRgb},0)`);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2); ctx.fill();

      // spinning swirl: a brighter core orbiting inside the blob, spinning
      // around it as it drifts and bounces
      const sx = b.x + Math.cos(b.spin) * b.r * 0.42;
      const sy = b.y + Math.sin(b.spin) * b.r * 0.42;
      const sr = b.r * 0.32;
      const g2 = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr);
      g2.addColorStop(0, `rgba(255,255,255,${0.35 * b.shade})`);
      g2.addColorStop(1, `rgba(${accentRgb},0)`);
      ctx.fillStyle = g2;
      ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
    }

    canvas.style.opacity = (!isCyberRadial() && !isDawningHorizon()) ? "0.6" : "0";
    blobState.raf = requestAnimationFrame(step);
  }

  blobState = { canvas, blobs, raf: null };
  step();
}

// ---------------- Dawning Horizon: dancing silk threads ---------------
// Several glowing threads sweep out from the left-center of the screen in
// slow, waving arcs (silk-in-the-wind motion via a growing sine wave along
// each thread's length), colored with the active section's accent. Sparks
// occasionally break off and drift up/down and rightward, fading as they
// go. Runs only behind Dawning Horizon; fades out otherwise, same
// stay-alive-but-invisible approach as the blob canvas.
let threadState = null;
function initSilkThreads() {
  if (threadState) return;
  const canvas = document.createElement("canvas");
  canvas.id = "silk-canvas";
  canvas.style.cssText = "position:fixed;inset:0;z-index:0;pointer-events:none;transition:opacity 500ms ease;";
  const horizon = el("horizon-glow");
  horizon.insertAdjacentElement("afterend", canvas);
  const ctx = canvas.getContext("2d");

  const THREAD_COUNT = 7;
  const threads = Array.from({ length: THREAD_COUNT }, (_, i) => ({
    phase: Math.random() * Math.PI * 2,
    speed: 0.006 + Math.random() * 0.006,
    ampY: 36 + Math.random() * 56,
    yOffset: (i - (THREAD_COUNT - 1) / 2) * 24,
    length: 0.55 + Math.random() * 0.35,
  }));
  let particles = [];

  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  function threadPoint(t, thr, w, h) {
    const originY = h / 2 + thr.yOffset;
    const x = t * w * thr.length;
    const wave = Math.sin(t * Math.PI * 2.2 + thr.phase) * thr.ampY * t; // amplitude grows with distance from the origin, like a swaying strand
    return { x, y: originY + wave };
  }

  function step() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const accentRgb = hexToRgbString(getComputedStyle(document.documentElement).getPropertyValue("--active-accent") || "#fbbf24");

    threads.forEach((thr) => {
      thr.phase += thr.speed;
      ctx.beginPath();
      const segments = 40;
      for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const p = threadPoint(t, thr, w, h);
        if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = `rgba(${accentRgb},0.5)`;
      ctx.lineWidth = 1.6;
      ctx.shadowColor = `rgba(${accentRgb},0.85)`;
      ctx.shadowBlur = 9;
      ctx.stroke();

      if (Math.random() < 0.06) {
        const t = Math.random();
        const p = threadPoint(t, thr, w, h);
        particles.push({ x: p.x, y: p.y, vx: 0.3 + Math.random() * 0.6, vy: (Math.random() - 0.5) * 1.2, life: 1, rgb: accentRgb });
      }
    });
    ctx.shadowBlur = 0;

    particles.forEach((p) => { p.x += p.vx; p.y += p.vy; p.vy += 0.01; p.life -= 0.012; });
    particles = particles.filter((p) => p.life > 0 && p.x < w + 20);
    particles.forEach((p) => {
      ctx.beginPath();
      ctx.fillStyle = `rgba(${p.rgb},${p.life})`;
      ctx.shadowColor = `rgba(${p.rgb},0.9)`;
      ctx.shadowBlur = 6;
      ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.shadowBlur = 0;

    canvas.style.opacity = isDawningHorizon() ? "0.8" : "0";
    threadState.raf = requestAnimationFrame(step);
  }

  threadState = { canvas, threads, raf: null };
  step();
}
async function boot() {
  tickClock();
  buildOsk();
  const [settings, kc] = await Promise.all([api().get_settings(), api().get_keyboard_controls()]);
  state.settings = settings;
  state.keyboardControls = kc;
  await loadFilterPresets(settings);
  state.categories = buildCategories(settings);

  el("hint-confirm").textContent = `${kc.confirm} select`;
  el("hint-back").textContent = `${kc.back} back`;

  applyAccent();
  renderCategories();
  applyBackground(settings);
  await applyOverlay(settings);
  await updateBatteryIndicator();
  await refreshItemPanel(); // show the first category's content immediately, live
  initBlobBackground();
  initSilkThreads();

  await playIntroIfConfigured();
}

if (window.pywebview) boot();
else window.addEventListener("pywebviewready", boot);
