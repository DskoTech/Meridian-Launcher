/* Meridian frontend — keyboard, mouse, and controller driven cross-bar UI.
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
};

const PALETTE = ["#60a5fa", "#f472b6", "#34d399", "#fb923c", "#e879f9", "#facc15", "#c084fc", "#38bdf8"];

// Note: Settings and System are appended in buildCategories(), in that
// order, so System always sits after Settings as the very last category.
const FIXED_CATEGORIES = [
  { id: "music", label: "Music", kind: "media", color: "var(--accent-music)" },
  { id: "photos", label: "Photos", kind: "media", color: "var(--accent-photos)" },
  { id: "videos", label: "Videos", kind: "media", color: "var(--accent-videos)" },
  { id: "apps", label: "Apps", kind: "exe_list", color: "var(--accent-apps)" },
  { id: "games", label: "Games", kind: "exe_list", color: "var(--accent-games)" },
  { id: "emulators", label: "Emulators", kind: "exe_list", color: "var(--accent-emulators)" },
  { id: "chat", label: "Chat", kind: "exe_list", color: "var(--accent-chat)" },
  { id: "streaming", label: "Streaming", kind: "exe_list", color: "var(--accent-streaming)" },
  { id: "web", label: "Web", kind: "web_list", color: "var(--accent-web)" },
  { id: "files", label: "Files", kind: "file_list", color: "var(--accent-files)" },
  { id: "macros", label: "Macros", kind: "macro_list", color: "var(--accent-macros)" },
];

// Web: CyberDeck Browser first, Default Browser second.
const WEB_ITEMS = [
  { id: "cyberdeck", label: "CyberDeck Browser", icon: "web" },
  { id: "default_browser", label: "Default Browser", icon: "web" },
];

// Files: Meridian Explorer first, Windows File Explorer second.
const FILE_ITEMS = [
  { id: "meridian_explorer", label: "Meridian Explorer", icon: "files" },
  { id: "windows_explorer", label: "Windows File Explorer", icon: "files" },
];

// Games: a permanent "Game Library" entry always sits at the top of the list.
const GAME_LIBRARY_ITEM = { __gameLibrary: true, name: "Game Library" };

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
  mediaFocus: "list", // "list" | "folders" — which column has left/right/up/down focus in Music/Photos/Videos
  folderEntries: [], // flattened navigable sidebar rows for the current media category
  folderCursor: 0,
  settingsCursor: 0, // controller/keyboard cursor over Settings' focusable controls
};

const el = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------------- clock & battery ----------------

function tickClock() {
  el("clock").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
setInterval(tickClock, 15000);

async function updateBatteryIndicator() {
  const ind = el("battery-indicator");
  const settings = state.settings;
  if (!settings || !settings.battery_indicator) { ind.classList.add("hidden"); return; }
  let status = await api().get_battery_status();
  if (!status) status = { percent: 100, plugged: true }; // desktop with no battery hardware — show full
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
  const custom = (settings.custom_sections || []).map((cs, i) => ({
    id: cs.id, label: cs.label, kind: "exe_list", color: PALETTE[i % PALETTE.length],
  }));
  const base = [...FIXED_CATEGORIES, ...custom];
  // Kiosk mode hides Settings and System entirely — the only ways back out
  // are the secret code, a 45s Y hold, or hand-editing settings.json.
  if (settings.window_mode === "kiosk") return base;
  return [
    ...base,
    { id: "settings", label: "Settings", kind: "settings", color: "var(--accent-settings)" },
    { id: "system", label: "System", kind: "system_list", color: "var(--accent-system)" },
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
  const row = el("category-row");
  row.style.transform = "translateX(0)";
  const activeIcon = row.querySelector(".category.active .icon-ring");
  const firstListIcon = el("item-panel").querySelector(".row-visual");
  if (!activeIcon || !firstListIcon) return;
  const activeRect = activeIcon.getBoundingClientRect();
  const listRect = firstListIcon.getBoundingClientRect();
  const delta = (listRect.left + listRect.width / 2) - (activeRect.left + activeRect.width / 2);
  row.style.transform = `translateX(${delta}px)`;
}

function applyAccent() {
  document.documentElement.style.setProperty("--active-accent", state.categories[state.catIndex].color);
}

// ---------------- category selection (always live, no separate "enter" step) ----------------

function selectCategory(i) {
  state.catIndex = i;
  state.selected = 0;
  state.mediaFocus = "list";
  state.settingsCursor = 0;
  applyAccent();
  renderCategories();
  refreshItemPanel();
}

function moveCategory(delta) {
  const next = (state.catIndex + delta + state.categories.length) % state.categories.length;
  selectCategory(next);
}

// Music/Photos/Videos, when Load Subfolders is off, show a folder sidebar
// to the left of the list. Left/Right there behaves differently from the
// usual "always changes category" rule: Left first moves focus into the
// sidebar; only pressing Left again (once already in the sidebar) moves to
// the section to the left. Right mirrors this back out to the file list.
function isSubfolderModeActive() {
  const cat = state.categories[state.catIndex];
  return !!(cat && cat.kind === "media" && state.settings && state.settings.load_subfolders === false);
}

function handleLeftNav() {
  if (isSubfolderModeActive()) {
    if (state.mediaFocus === "list") {
      state.mediaFocus = "folders";
      renderSubfolderSidebar(state.categories[state.catIndex].id);
      return;
    }
    moveCategory(-1); // already in the folder sidebar: move to the section to the left
    return;
  }
  moveCategory(-1);
}

function handleRightNav() {
  if (isSubfolderModeActive() && state.mediaFocus === "folders") {
    state.mediaFocus = "list";
    renderSubfolderSidebar(state.categories[state.catIndex].id);
    return;
  }
  moveCategory(1);
}

function moveSelection(delta) {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "direct") return; // no linear list to browse there
  if (cat.kind === "settings") {
    const count = settingsFocusableElements().length;
    if (!count) return;
    state.settingsCursor = Math.max(0, Math.min(count - 1, state.settingsCursor + delta));
    highlightSettingsCursor();
    return;
  }
  if (isSubfolderModeActive() && state.mediaFocus === "folders") {
    const entries = state.folderEntries || [];
    if (!entries.length) return;
    state.folderCursor = Math.max(0, Math.min(entries.length - 1, state.folderCursor + delta));
    renderSubfolderSidebar(cat.id);
    return;
  }
  if (!state.items.length) return;
  state.selected = Math.max(0, Math.min(state.items.length - 1, state.selected + delta));
  renderItemList(cat);
}

// ---------------- filling the panel for whatever category is highlighted ----------------

async function refreshItemPanel() {
  const cat = state.categories[state.catIndex];
  try {
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
    } else if (cat.kind === "web_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      state.items = WEB_ITEMS;
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
    } else if (cat.kind === "exe_list") {
      el("subfolder-nav").classList.add("hidden");
      el("preview-pane").classList.add("hidden");
      const items = await api().list_section_items(cat.id);
      state.items = cat.id === "games" ? [GAME_LIBRARY_ITEM, ...items] : (items.length ? items : [{ __empty: true }]);
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
  state.folderEntries = buildFolderEntries(kind, roots);
  state.folderCursor = Math.max(0, Math.min(state.folderCursor, state.folderEntries.length - 1));
  renderSubfolderSidebar(kind);
  renderItemList(state.categories[state.catIndex]);
}

function buildFolderEntries(kind, roots) {
  const stack = state.folderStack[kind] || [];
  const entries = roots.map((r) => ({ type: "root", path: r }));
  if (stack.length > 1) entries.push({ type: "up" });
  (state.subfoldersCurrent || []).forEach((name) => entries.push({ type: "subfolder", name }));
  return entries;
}

async function activateFolderEntry(kind, entry) {
  if (entry.type === "root") {
    state.folderStack[kind] = [entry.path];
    state.folderCursor = 0;
    await loadCurrentBrowsePath(kind);
  } else if (entry.type === "up") {
    await goUpFolder(kind);
    state.folderCursor = 0;
  } else if (entry.type === "subfolder") {
    await enterSubfolder(kind, entry.name);
    state.folderCursor = 0;
  }
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

function renderSubfolderSidebar(kind) {
  const nav = el("subfolder-nav");
  nav.classList.toggle("focused", state.mediaFocus === "folders");
  nav.innerHTML = `<div class="sf-header">Folders</div>`;
  const stack = state.folderStack[kind] || [];
  const currentRoot = stack[0];

  (state.folderEntries || []).forEach((entry, i) => {
    const row = document.createElement("div");
    const isCursor = state.mediaFocus === "folders" && i === state.folderCursor;
    let iconSvg, label, isCurrentRoot = false;
    if (entry.type === "root") {
      iconSvg = FOLDER_ICON_SVG;
      label = entry.path.split(/[\\/]/).filter(Boolean).pop() || entry.path;
      isCurrentRoot = entry.path === currentRoot;
    } else if (entry.type === "up") {
      iconSvg = UP_ICON_SVG;
      label = ".. Up";
    } else {
      iconSvg = FOLDER_ICON_SVG;
      label = entry.name;
    }
    row.className = "sf-row" + (isCursor ? " selected" : "") + (isCurrentRoot ? " current-root" : "");
    row.innerHTML = `${iconSvg}<span class="sf-label">${escapeHtml(label)}</span>`;
    row.addEventListener("click", () => {
      state.mediaFocus = "folders";
      state.folderCursor = i;
      activateFolderEntry(kind, entry);
    });
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

function rowContentFor(cat, item, i) {
  if (item.__browsingEmpty) {
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">This folder is empty</div></div>`;
  }
  if (item.__empty) {
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">Nothing added yet — press confirm to add it in Settings</div></div>`;
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
    if (item.__gameLibrary) {
      return `<div class="row-visual">${ICONS.games}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
    }
    const iconHtml = item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : iconFor(cat.id);
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
  }
  if (cat.kind === "macro_list") {
    const iconHtml = item.type === "builtin" ? ICONS.macros : (item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : ICONS.bat);
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
  }
  if (cat.kind === "system_list" || cat.kind === "file_list" || cat.kind === "web_list") {
    return `<div class="row-visual">${ICONS[item.icon]}</div><div class="meta"><div class="title">${escapeHtml(item.label)}</div></div>`;
  }
  return "";
}

function renderItemList(cat) {
  const wrap = document.createElement("div");
  wrap.className = "item-list";
  state.items.forEach((item, i) => {
    const row = document.createElement("div");
    const isEmpty = !!item.__empty || !!item.__browsingEmpty;
    row.className = "item-row" + (i === state.selected ? " selected" : "") + (isEmpty ? " empty-prompt-row" : "");
    row.innerHTML = rowContentFor(cat, item, i);
    row.addEventListener("click", () => { state.selected = i; renderItemList(cat); activateCurrentSelection(); });
    wrap.appendChild(row);
  });
  el("item-panel").innerHTML = "";
  el("item-panel").appendChild(wrap);
  const activeEl = wrap.querySelector(".selected");
  if (activeEl && typeof activeEl.scrollIntoView === "function") activeEl.scrollIntoView({ block: "nearest" });
  updatePreviewPane();
  alignCategoryRowToList();
}

// ---------------- activating whatever is currently selected ----------------

async function activateCurrentSelection() {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "settings") {
    const els = settingsFocusableElements();
    const node = els[state.settingsCursor];
    if (node) node.click();
    return;
  }

  if (isSubfolderModeActive() && state.mediaFocus === "folders") {
    const entry = (state.folderEntries || [])[state.folderCursor];
    if (entry) await activateFolderEntry(cat.id, entry);
    return;
  }

  const item = state.items[state.selected];
  if (!item) return;
  if (item.__browsingEmpty) return; // just an inert "this folder is empty" placeholder
  if (item.__empty) { await goToSettingsFor(cat); return; }
  if (item.__gameLibrary) { await activateGameLibrary(); return; }

  if (cat.id === "music") playMusicAt(state.selected);
  else if (cat.id === "photos") openPhoto(state.selected);
  else if (cat.id === "videos") openVideo(state.selected);
  else if (cat.kind === "exe_list") launchAndNotify(item.path, cat.id);
  else if (cat.kind === "macro_list") activateMacro(item);
  else if (cat.kind === "system_list") activateSystemItem(item);
  else if (cat.kind === "file_list") activateFileItem(item);
  else if (cat.kind === "web_list") activateWebItem(item);
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

async function launchAndNotify(path, sectionId) {
  const res = await api().launch_exe(path, sectionId);
  if (!res.ok) showToast(`Couldn't launch: ${res.error}`);
}

async function activateGameLibrary() {
  const res = await api().launch_game_library();
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
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

async function activateWebItem(item) {
  const res = item.id === "cyberdeck" ? await api().launch_cyberdeck() : await api().open_web();
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

// ---------------- generic Yes/No confirm modal (kiosk enable, factory reset) ----------------
// Controller/keyboard navigable like everything else: left/right swaps the
// highlighted button, confirm picks it, back always counts as "No".

let confirmResolveFn = null;
let confirmCursor = 1; // default to "No" — both callers are consequential actions

function isConfirmOpen() {
  return !el("confirm-overlay").classList.contains("hidden");
}

function openConfirmModal(title, message) {
  return new Promise((resolve) => {
    confirmResolveFn = resolve;
    confirmCursor = 1;
    el("confirm-title").textContent = title;
    el("confirm-message").textContent = message;
    el("confirm-overlay").classList.remove("hidden");
    highlightConfirmCursor();
  });
}

function closeConfirmModal(result) {
  el("confirm-overlay").classList.add("hidden");
  const fn = confirmResolveFn;
  confirmResolveFn = null;
  if (fn) fn(result);
}

function highlightConfirmCursor() {
  el("confirm-yes").classList.toggle("settings-focus", confirmCursor === 0);
  el("confirm-no").classList.toggle("settings-focus", confirmCursor === 1);
}

function handleConfirmOverlayInput(action) {
  if (action === "left" || action === "right") {
    confirmCursor = confirmCursor === 0 ? 1 : 0;
    highlightConfirmCursor();
  } else if (action === "confirm") {
    closeConfirmModal(confirmCursor === 0);
  } else if (action === "back") {
    closeConfirmModal(false);
  }
}

el("confirm-yes").addEventListener("click", () => closeConfirmModal(true));
el("confirm-no").addEventListener("click", () => closeConfirmModal(false));

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
  const c = document.createElement("div");

  // media folders
  ["music", "photos", "videos"].forEach((kind) => {
    const block = document.createElement("div");
    block.className = "settings-block";
    block.id = `settings-block-${kind}`;
    block.innerHTML = `<h3>${kind} folders</h3>`;
    (settings.folders[kind] || []).forEach((f) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(f)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => { await api().remove_folder(kind, f); renderSettings(); });
      block.appendChild(row);
    });
    const addBtn = document.createElement("button");
    addBtn.className = "add-folder-btn";
    addBtn.textContent = "+ Add folder";
    addBtn.addEventListener("click", async () => {
      const folder = await api().pick_folder();
      if (folder) { await api().add_folder(kind, folder); renderSettings(); }
    });
    block.appendChild(addBtn);
    c.appendChild(block);
  });

  // Load Subfolders (between Video folders and Apps, as requested)
  c.appendChild(buildToggleBlock(
    "Load Subfolders",
    settings.load_subfolders,
    async () => { await api().set_load_subfolders(!settings.load_subfolders); renderSettings(); },
    settings.load_subfolders
      ? "Enabled — Music/Photos/Videos scan all subfolders automatically"
      : "Disabled — browse folders manually in Music/Photos/Videos",
  ));

  // exe-list sections: apps/games/emulators/chat/streaming + custom sections
  const exeSections = [
    { id: "apps", label: "Apps" }, { id: "games", label: "Games" },
    { id: "emulators", label: "Emulators" }, { id: "chat", label: "Chat" },
    { id: "streaming", label: "Streaming" },
    ...(settings.custom_sections || []).map((cs) => ({ id: cs.id, label: cs.label, custom: true })),
  ];
  exeSections.forEach((sec) => c.appendChild(buildExeSectionBlock(sec, settings)));

  // add custom section
  const addSectionBtn = document.createElement("button");
  addSectionBtn.className = "btn-outline";
  addSectionBtn.textContent = "+ Add custom section";
  addSectionBtn.addEventListener("click", openSectionModal);
  const sectionBlockWrap = document.createElement("div");
  sectionBlockWrap.className = "settings-block";
  sectionBlockWrap.appendChild(addSectionBtn);
  c.appendChild(sectionBlockWrap);

  // macros
  c.appendChild(await buildMacroSectionBlock());

  // window mode
  const winBlock = document.createElement("div");
  winBlock.className = "settings-block";
  winBlock.innerHTML = `<h3>Window mode</h3>`;
  const radioWrap = document.createElement("div");
  radioWrap.className = "radio-group";
  ["fullscreen", "windowed", "kiosk"].forEach((mode) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + (settings.window_mode === mode ? " active" : "");
    pill.textContent = mode[0].toUpperCase() + mode.slice(1);
    pill.addEventListener("click", async () => {
      if (mode === "kiosk") {
        if (settings.window_mode === "kiosk") return;
        const yes = await openConfirmModal(
          "Enable kiosk mode?",
          "You sure you want to enable kiosk mode?This can only be disabled by editing the json settings, holding the controllers y button for 45 seconds, or entering the code dpad up, dpad up, dpad down, dpad down, dpad left, dpad right, dpad left, dpad right, b button, a button; or up key, up key, down key, down key, left key, right key, left key, right key, b key, a key."
        );
        await api().set_window_mode(yes ? "kiosk" : "fullscreen");
        await applyKioskChangeAndRefresh();
        return;
      }
      await api().set_window_mode(mode);
      renderSettings();
    });
    radioWrap.appendChild(pill);
  });
  winBlock.appendChild(radioWrap);
  c.appendChild(winBlock);

  // video fullscreen
  c.appendChild(buildToggleBlock(
    "Video Fullscreen",
    settings.video_fullscreen,
    async () => { await api().set_video_fullscreen(!settings.video_fullscreen); renderSettings(); },
  ));

  // battery indicator
  c.appendChild(buildToggleBlock(
    "Battery Level Indicator",
    settings.battery_indicator,
    async () => { await api().set_battery_indicator(!settings.battery_indicator); renderSettings(); updateBatteryIndicator(); },
  ));

  // launch external system features (Task Manager, Control Panel, Recycle
  // Bin, Uninstall Apps, "open Windows Bluetooth settings") with osm.bat
  c.appendChild(buildToggleBlock(
    "Launch External System features with onscreenmenu?",
    settings.launch_system_with_osm,
    async () => { await api().set_system_osm(!settings.launch_system_with_osm); renderSettings(); },
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

  // opening video
  const vidBlock = document.createElement("div");
  vidBlock.className = "settings-block";
  vidBlock.innerHTML = `<h3>Opening video</h3>`;
  const vidBtn = document.createElement("button");
  vidBtn.className = "btn-outline";
  vidBtn.textContent = settings.opening_video ? "Change video" : "Choose video";
  vidBtn.addEventListener("click", async () => { await api().set_opening_video(); renderSettings(); });
  vidBlock.appendChild(vidBtn);
  if (settings.opening_video) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_opening_video(); renderSettings(); });
    vidBlock.appendChild(clear);
  }
  c.appendChild(vidBlock);

  const hasFfmpeg = await api().has_ffmpeg();
  if (!hasFfmpeg) {
    const note = document.createElement("div");
    note.className = "empty-msg";
    note.textContent = "ffmpeg not found — video thumbnails and durations are limited until it's installed and on PATH.";
    c.appendChild(note);
  }

  // revert to factory settings — always the very last option
  const resetBlock = document.createElement("div");
  resetBlock.className = "settings-block";
  resetBlock.id = "settings-block-factory-reset";
  resetBlock.innerHTML = `<h3>Reset</h3>`;
  const resetBtn = document.createElement("button");
  resetBtn.className = "btn-outline btn-danger";
  resetBtn.textContent = "Revert to factory settings";
  resetBtn.addEventListener("click", async () => {
    const yes = await openConfirmModal(
      "Revert to factory settings?",
      "This clears out all saved user modifications — folders, sections, custom sections, toggles, background/overlay/opening video, and window mode. This cannot be undone.",
    );
    if (!yes) return;
    await api().factory_reset();
    await refreshCategoriesAndLand();
    applyBackground(state.settings);
    await applyOverlay(state.settings);
    await updateBatteryIndicator();
    showToast("Factory settings restored.");
  });
  resetBlock.appendChild(resetBtn);
  c.appendChild(resetBlock);

  panel.appendChild(c);
  alignCategoryRowToList();
  const focusCount = settingsFocusableElements().length;
  state.settingsCursor = focusCount ? Math.max(0, Math.min(focusCount - 1, state.settingsCursor)) : 0;
  highlightSettingsCursor();
}

// Settings is controller/keyboard navigable like every other section: Up/Down
// moves a cursor over its buttons/toggles/radio-pills (in visual order),
// confirm clicks whichever one is highlighted. Native inputs (the custom
// section name field, the Wi-Fi password field) aren't part of this list —
// they get real focus directly when their modal opens.
function settingsFocusableElements() {
  return [...el("item-panel").querySelectorAll("button, .toggle-switch, .radio-pill")];
}

function highlightSettingsCursor() {
  const els = settingsFocusableElements();
  els.forEach((node, i) => node.classList.toggle("settings-focus", i === state.settingsCursor));
  const current = els[state.settingsCursor];
  if (current && typeof current.scrollIntoView === "function") current.scrollIntoView({ block: "nearest" });
}

function buildExeSectionBlock(sec, settings) {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.id = `settings-block-${sec.id}`;
  const h = document.createElement("h3");
  h.textContent = sec.label;
  block.appendChild(h);

  const secSettings = (settings.sections && settings.sections[sec.id]) || {};
  const osmOn = secSettings.launch_with_osm !== false; // default on
  const osmRow = document.createElement("div");
  osmRow.className = "settings-row";
  const osmToggle = document.createElement("div");
  osmToggle.className = "toggle-switch" + (osmOn ? " on" : "");
  osmToggle.innerHTML = `<div class="knob"></div>`;
  osmToggle.addEventListener("click", async () => {
    await api().set_section_osm(sec.id, !osmOn);
    renderSettings();
  });
  osmRow.appendChild(osmToggle);
  osmRow.appendChild(document.createTextNode("Launch with onscreenmenu?"));
  block.appendChild(osmRow);

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
    || !el("network-overlay").classList.contains("hidden")
    || isConfirmOpen();
}

function handleBack() {
  if (!el("video-overlay").classList.contains("hidden")) { closeVideo(); return; }
  if (!el("photo-overlay").classList.contains("hidden")) { closePhoto(); return; }
  if (!el("modal-overlay").classList.contains("hidden")) { closeSectionModal(); return; }
  if (!el("wifi-password-overlay").classList.contains("hidden")) { closeWifiPasswordModal(); return; }
  if (!el("network-overlay").classList.contains("hidden")) { closeNetworkOverlay(); return; }
  if (isConfirmOpen()) { handleConfirmOverlayInput("back"); return; }
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

  if (isConfirmOpen()) {
    if (e.key === "ArrowLeft" || (kc && e.key === kc.left)) { handleConfirmOverlayInput("left"); return; }
    if (e.key === "ArrowRight" || (kc && e.key === kc.right)) { handleConfirmOverlayInput("right"); return; }
    if (kc && e.key === kc.confirm && !e.repeat) { handleConfirmOverlayInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleConfirmOverlayInput("back"); return; }
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
  else if (e.key === kc.up) moveSelection(-1);
  else if (e.key === kc.down) moveSelection(1);
  else if (e.key === kc.left) handleLeftNav();
  else if (e.key === kc.right) handleRightNav();
});

// ---------------- controller bridge (called from Python via evaluate_js) ----------------
// Note: confirm/back are already edge-triggered on the Python side (XInput
// rising-edge detection), so no repeat-guard is needed here for those.

window.handleControllerInput = function (action) {
  if (!state.introDismissed) return;
  if (isOskCapturing()) { handleOskControllerInput(action); return; }
  if (!el("video-overlay").classList.contains("hidden")) { handleVideoControllerInput(action); return; }
  if (isConfirmOpen()) { handleConfirmOverlayInput(action); return; }
  if (isOverlayOpen()) {
    if (action === "left" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (action === "right" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (action === "back") handleBack();
    return;
  }
  if (action === "confirm") activateCurrentSelection();
  else if (action === "back") handleBack();
  else if (action === "up") moveSelection(-1);
  else if (action === "down") moveSelection(1);
  else if (action === "left") handleLeftNav();
  else if (action === "right") handleRightNav();
};

window.handleControllerAny = function () {
  if (!state.introDismissed && window._dismissIntro) window._dismissIntro();
};

// ---------------- kiosk mode: secret unlock code ----------------
// Works from anywhere, any time, regardless of what's on screen — matches
// physical DPAD/A/B on a controller or the literal arrow/b/a keys on a
// keyboard, independent of whatever confirm/back/etc. are remapped to.

const KIOSK_CODE_CONTROLLER = ["DPAD_UP", "DPAD_UP", "DPAD_DOWN", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "DPAD_LEFT", "DPAD_RIGHT", "B", "A"];
const KIOSK_CODE_KEYBOARD = ["arrowup", "arrowup", "arrowdown", "arrowdown", "arrowleft", "arrowright", "arrowleft", "arrowright", "b", "a"];
let controllerCodeBuffer = [];
let keyboardCodeBuffer = [];

window.handleRawControllerButton = function (name) {
  controllerCodeBuffer.push(name);
  if (controllerCodeBuffer.length > KIOSK_CODE_CONTROLLER.length) controllerCodeBuffer.shift();
  if (controllerCodeBuffer.length === KIOSK_CODE_CONTROLLER.length
      && controllerCodeBuffer.every((v, i) => v === KIOSK_CODE_CONTROLLER[i])) {
    controllerCodeBuffer = [];
    tryDisableKioskViaCode();
  }
};

document.addEventListener("keydown", (e) => {
  if (!state.introDismissed) return;
  const key = e.key.toLowerCase();
  if (!["arrowup", "arrowdown", "arrowleft", "arrowright", "b", "a"].includes(key)) return;
  keyboardCodeBuffer.push(key);
  if (keyboardCodeBuffer.length > KIOSK_CODE_KEYBOARD.length) keyboardCodeBuffer.shift();
  if (keyboardCodeBuffer.length === KIOSK_CODE_KEYBOARD.length
      && keyboardCodeBuffer.every((v, i) => v === KIOSK_CODE_KEYBOARD[i])) {
    keyboardCodeBuffer = [];
    tryDisableKioskViaCode();
  }
});

async function tryDisableKioskViaCode() {
  if (!state.settings || state.settings.window_mode !== "kiosk") return;
  const res = await api().disable_kiosk_via_code();
  if (res && res.ok) await exitKioskModeAndNotify();
}

// Rebuilds state.categories from current settings (Settings/System appear
// or disappear depending on kiosk state) and lands on a sane category if
// the one being viewed just vanished. Shared by every path that can flip
// kiosk mode in either direction.
async function refreshCategoriesAndLand() {
  const settings = await api().get_settings();
  state.settings = settings;
  const currentId = state.categories[state.catIndex] && state.categories[state.catIndex].id;
  state.categories = buildCategories(settings);
  let idx = state.categories.findIndex((c) => c.id === currentId);
  if (idx === -1) idx = 0;
  state.catIndex = idx;
  state.selected = 0;
  applyAccent();
  renderCategories();
  await refreshItemPanel();
}

async function applyKioskChangeAndRefresh() {
  await refreshCategoriesAndLand();
}

// Shared by every kiosk-exit path (secret code, 45s Y hold): refreshes the
// category list (Settings/System reappear), lands somewhere sane if the
// currently-viewed category just vanished, and confirms with a toast.
async function exitKioskModeAndNotify() {
  await refreshCategoriesAndLand();
  showToast("kiosk mode disabled");
}

window.onKioskDisabledExternally = function () { exitKioskModeAndNotify(); };

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
