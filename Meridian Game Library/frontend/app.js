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
    loggedInCheck: (s) => !!(s.playnite && s.playnite.export_available),
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
  gridFocus: "list", // "list" | "filter" — which pane has directional focus in a game_grid section
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

function buildCategories(settings) {
  return [
    ...FIXED_CATEGORIES,
    { id: "settings", label: "Settings", kind: "settings", color: "var(--accent-settings)" },
  ];
}

function iconFor(catId) {
  return ICONS[catId] || ICONS.generic;
}

// ---------------- category row: circular carousel with FLIP sliding ----------------

const categoryElements = new Map(); // id -> persistent DOM node, so transitions can animate

function computeDisplayOrder() {
  const n = state.categories.length;
  const start = state.catIndex <= CAROUSEL_ANCHOR ? 0 : state.catIndex - CAROUSEL_ANCHOR;
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
    wrap.classList.toggle("active", realIdx === state.catIndex);
    frag.appendChild(wrap);
  });
  row.innerHTML = "";
  row.appendChild(frag);

  // FLIP part 2: animate from the old position to the new one
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const elx = categoryElements.get(cat.id);
    const oldRect = oldRects.get(cat.id);
    if (!oldRect) { elx.style.transition = ""; elx.style.transform = ""; return; }
    const newRect = elx.getBoundingClientRect();
    const dx = oldRect.left - newRect.left;
    if (Math.abs(dx) > 0.5) {
      elx.style.transition = "none";
      elx.style.transform = `translateX(${dx}px)`;
      requestAnimationFrame(() => {
        elx.style.transition = "transform 320ms ease";
        elx.style.transform = "translateX(0)";
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
}

// ---------------- category selection (always live, no separate "enter" step) ----------------

function selectCategory(i) {
  state.catIndex = i;
  state.selected = 0;
  state.gridFocus = "list";
  applyAccent();
  renderCategories();
  refreshItemPanel();
}

function moveCategory(delta) {
  const next = (state.catIndex + delta + state.categories.length) % state.categories.length;
  selectCategory(next);
}

// Normal XMB rule everywhere else: Left/Right always changes category,
// Up/Down always browses the list. game_grid sections add one more stop
// in between: Left from the game list moves focus to the filter sidebar
// instead of changing category; from the filter sidebar, Left continues
// on to the previous category (and Right comes back to the game list,
// same category). Up/Down on the filter sidebar cycles the three filter
// options instead of browsing games.
function isGameGridCategory() {
  const cat = state.categories[state.catIndex];
  return !!cat && cat.kind === "game_grid";
}

// Must match the grid's column count in style.css (.channel-grid's
// grid-template-columns: repeat(5, 1fr)) — if that ever changes, update
// this too so Up/Down keep landing in the same visual column.
const GRID_COLUMNS = 5;

function currentGridRowBounds() {
  const rowStart = Math.floor(state.selected / GRID_COLUMNS) * GRID_COLUMNS;
  const rowEnd = Math.min(rowStart + GRID_COLUMNS - 1, state.items.length - 1);
  return { rowStart, rowEnd };
}

// Up/Down/Left/Right all move within the grid itself now. Left/Right
// still double as the way in and out of it, the same idea as before: run
// off the left edge of a row and you land on the filter sidebar instead
// of wrapping to the previous row; run off the right edge and you move to
// the next section instead of wrapping to the next row — the grid's own
// edges are where the "zoom out" to filter/section navigation lives.
function handleDirectionalLeft() {
  if (isGameGridCategory()) {
    if (state.gridFocus === "filter") {
      moveCategory(-1); // already on the filter sidebar — continue on to the previous section
      return;
    }
    const { rowStart } = currentGridRowBounds();
    if (state.selected > rowStart) {
      moveSelection(-1);
    } else {
      state.gridFocus = "filter";
      renderGameFilterSidebar(state.categories[state.catIndex]);
    }
    return;
  }
  moveCategory(-1);
}

function handleDirectionalRight() {
  if (isGameGridCategory()) {
    if (state.gridFocus === "filter") {
      state.gridFocus = "list";
      renderGameFilterSidebar(state.categories[state.catIndex]);
      return;
    }
    const { rowEnd } = currentGridRowBounds();
    if (state.selected < rowEnd) {
      moveSelection(1);
    } else {
      moveCategory(1);
    }
    return;
  }
  moveCategory(1);
}

function handleDirectionalUp() {
  if (isGameGridCategory() && state.gridFocus === "filter") { moveFilterSelection(-1); return; }
  if (isGameGridCategory() && state.gridFocus === "list") { moveSelection(-GRID_COLUMNS); return; }
  moveSelection(-1);
}

function handleDirectionalDown() {
  if (isGameGridCategory() && state.gridFocus === "filter") { moveFilterSelection(1); return; }
  if (isGameGridCategory() && state.gridFocus === "list") { moveSelection(GRID_COLUMNS); return; }
  moveSelection(1);
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
  const cfg = STORE_CONFIG[cat.store];

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
    const cfg = STORE_CONFIG[cat.store];
    // item.art is already a ready-to-use URL (http, or the app's own local
    // media server for local files) by the time it reaches the frontend —
    // see main.py's _entries_with_media_urls. Raw file:// paths aren't
    // reliable in this webview backend, so the backend never sends one.
    const artHtml = item.art ? `<img src="${item.art}" alt="" data-fallback-icon>` : iconFor(cat.id);
    return `
      <div class="tile-art">${artHtml}</div>
      <div class="tile-title">${escapeHtml(item.title)}</div>
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

function renderItemList(cat) {
  const isGrid = cat.kind === "game_grid";
  const wrap = document.createElement("div");
  wrap.className = isGrid ? "channel-grid" : "item-list";
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
  const cfg = STORE_CONFIG[cat.store];
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
    const cfg = STORE_CONFIG[cat.store];
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
  const panel = el("item-panel");
  panel.innerHTML = "";
  panel.classList.remove("wide");
  const c = document.createElement("div");

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

  if (!kc) return;
  if (e.key === kc.confirm) { if (!e.repeat) activateCurrentSelection(); }
  else if (e.key === kc.back) { if (!e.repeat) handleBack(); }
  else if (e.key === kc.up) handleDirectionalUp();
  else if (e.key === kc.down) handleDirectionalDown();
  else if (e.key === kc.left) handleDirectionalLeft();
  else if (e.key === kc.right) handleDirectionalRight();
});

// ---------------- controller bridge (called from Python via evaluate_js) ----------------
// Note: confirm/back are already edge-triggered on the Python side (XInput
// rising-edge detection), so no repeat-guard is needed here for those.

window.handleControllerInput = function (action) {
  if (!state.introDismissed) return;
  if (isOskCapturing()) { handleOskControllerInput(action); return; }
  if (!el("video-overlay").classList.contains("hidden")) { handleVideoControllerInput(action); return; }
  if (isOverlayOpen()) {
    if (action === "left" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (action === "right" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (action === "back") handleBack();
    return;
  }
  if (action === "confirm") activateCurrentSelection();
  else if (action === "back") handleBack();
  else if (action === "up") handleDirectionalUp();
  else if (action === "down") handleDirectionalDown();
  else if (action === "left") handleDirectionalLeft();
  else if (action === "right") handleDirectionalRight();
};

window.handleControllerAny = function () {
  if (!state.introDismissed && window._dismissIntro) window._dismissIntro();
};

// ---------------- boot ----------------

async function boot() {
  tickClock();
  buildOsk();
  const [settings, kc] = await Promise.all([api().get_settings(), api().get_keyboard_controls()]);
  state.settings = settings;
  state.keyboardControls = kc;
  state.categories = buildCategories(settings);

  el("hint-confirm").textContent = `${kc.confirm} select`;
  el("hint-back").textContent = `${kc.back} back`;

  applyAccent();
  renderCategories();
  applyBackground(settings);
  await applyOverlay(settings);
  await updateBatteryIndicator();
  await refreshItemPanel(); // show the first category's content immediately, live

  await playIntroIfConfigured();
}

if (window.pywebview) boot();
else window.addEventListener("pywebviewready", boot);
