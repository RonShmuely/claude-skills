/**
 * pins.js — floating pin-annotation overlay for the swarm dashboard.
 * Loaded via ?pins=1 query param. Self-executing IIFE.
 * Exposes window.__pins = { getPins, clearUI, destroy }
 */
(function () {
  "use strict";

  // ── Guard: only run when ?pins=1 ─────────────────────────────────────────
  if (new URLSearchParams(location.search).get("pins") !== "1") return;

  // ── Teardown any previous injection ──────────────────────────────────────
  if (window.__pins && typeof window.__pins.destroy === "function") {
    window.__pins.destroy();
  }

  // ─────────────────────────────────────────────────────────────────────────
  // State
  // ─────────────────────────────────────────────────────────────────────────
  let pickMode = false;
  let hoverTarget = null;      // currently hovered [data-pin-entity] element
  let hoverLabel = null;       // floating label el
  let openPopup = null;        // note popup el
  let openMenu = null;         // badge context menu el
  const badgeMap = new Map();  // pin id → badge el

  // ─────────────────────────────────────────────────────────────────────────
  // CSS injection
  // ─────────────────────────────────────────────────────────────────────────
  const STYLE_ID = "__pins-style";
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* ── toolbar ─────────────────────────────────────────── */
      #__pins-toolbar {
        position: fixed;
        top: 56px;
        right: 14px;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 6px;
        background: #0e0e0e;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 8px 6px;
        box-shadow: 0 4px 24px rgba(0,0,0,.6);
        font-family: 'JetBrains Mono', 'Geist Mono', ui-monospace, monospace;
      }
      #__pins-toolbar button {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        border: 1px solid #2a2a2a;
        border-radius: 5px;
        background: #141414;
        color: #bbb;
        font-size: 11px;
        letter-spacing: .08em;
        text-transform: uppercase;
        cursor: pointer;
        transition: background .12s, color .12s, border-color .12s;
        white-space: nowrap;
      }
      #__pins-toolbar button:hover { background: #1e1e1e; color: #fff; }
      #__pins-toolbar button.__pins-active {
        background: #2d0a2d;
        border-color: #c060c0;
        color: #e090e0;
        box-shadow: 0 0 8px rgba(192,80,192,.35);
      }

      /* ── hover label ──────────────────────────────────────── */
      #__pins-hover-label {
        position: fixed;
        z-index: 10001;
        padding: 3px 8px;
        background: rgba(10,10,10,.92);
        border: 1px solid #5a3a7a;
        border-radius: 4px;
        color: #d8a0d8;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 10px;
        letter-spacing: .06em;
        pointer-events: none;
        white-space: nowrap;
      }

      /* ── hover target outline ─────────────────────────────── */
      .__pins-target-hover {
        outline: 2px dashed #b060c0 !important;
        outline-offset: 2px;
      }

      /* ── pick-mode cursor hint ────────────────────────────── */
      body.__pins-pick-mode * {
        cursor: crosshair !important;
      }

      /* ── badges ───────────────────────────────────────────── */
      .pins-badge {
        position: absolute;
        z-index: 9999;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #e075a0;
        color: #fff;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 9px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border: 1.5px solid #ff99c0;
        box-shadow: 0 2px 8px rgba(220,80,130,.5);
        transition: opacity .3s, transform .15s;
        user-select: none;
      }
      .pins-badge:hover { transform: scale(1.18); }
      .pins-badge.resolved {
        opacity: 0;
        pointer-events: none;
      }

      /* ── badge context menu ───────────────────────────────── */
      .pins-badge-menu {
        position: fixed;
        z-index: 10002;
        min-width: 200px;
        max-width: 280px;
        background: #111;
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        padding: 10px 12px;
        box-shadow: 0 6px 28px rgba(0,0,0,.7);
        font-family: -apple-system, 'Segoe UI', sans-serif;
      }
      .pins-badge-menu .pins-note-text {
        font-size: 12px;
        color: #ccc;
        margin-bottom: 10px;
        line-height: 1.5;
        min-height: 18px;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .pins-badge-menu .pins-note-text:empty::before {
        content: '(no note)';
        color: #555;
        font-style: italic;
      }
      .pins-badge-menu .pins-menu-actions {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .pins-badge-menu button {
        padding: 3px 9px;
        font-size: 10px;
        border-radius: 4px;
        border: 1px solid #333;
        background: #1a1a1a;
        color: #aaa;
        cursor: pointer;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: .06em;
        text-transform: uppercase;
        transition: background .1s, color .1s;
      }
      .pins-badge-menu button:hover { background: #2a2a2a; color: #fff; }
      .pins-badge-menu button.pins-resolve-btn:hover { background: #0a2a0a; border-color: #40a040; color: #80d880; }
      .pins-badge-menu button.pins-delete-btn:hover  { background: #2a0a0a; border-color: #a04040; color: #d88080; }

      /* ── note popup ───────────────────────────────────────── */
      .pins-note-popup {
        position: fixed;
        z-index: 10003;
        min-width: 220px;
        background: #0e0e0e;
        border: 1px solid #5a3a7a;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 6px 28px rgba(0,0,0,.7);
        font-family: -apple-system, 'Segoe UI', sans-serif;
      }
      .pins-note-popup textarea {
        width: 100%;
        min-height: 68px;
        background: #161616;
        border: 1px solid #333;
        border-radius: 4px;
        color: #e5e5e5;
        font-family: -apple-system, 'Segoe UI', sans-serif;
        font-size: 12px;
        padding: 6px 8px;
        resize: vertical;
        outline: none;
        box-sizing: border-box;
      }
      .pins-note-popup textarea:focus { border-color: #8040a0; }
      .pins-note-popup .pins-popup-hint {
        font-size: 9px;
        color: #555;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        margin: 5px 0 7px;
        letter-spacing: .04em;
      }
      .pins-note-popup .pins-popup-actions {
        display: flex;
        gap: 6px;
      }
      .pins-note-popup button {
        padding: 3px 10px;
        font-size: 10px;
        border-radius: 4px;
        border: 1px solid #333;
        background: #181818;
        color: #aaa;
        cursor: pointer;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: .07em;
        text-transform: uppercase;
        transition: background .1s, color .1s;
      }
      .pins-note-popup .pins-save-btn {
        border-color: #6040a0;
        background: #1e0e2e;
        color: #c080e0;
      }
      .pins-note-popup .pins-save-btn:hover { background: #2a1040; color: #e0a0ff; }
      .pins-note-popup button:hover { background: #222; color: #ddd; }

      /* ── list panel ───────────────────────────────────────── */
      #__pins-list-panel {
        position: fixed;
        top: 56px;
        right: 110px;
        z-index: 10000;
        width: 320px;
        max-height: 80vh;
        overflow-y: auto;
        background: #0e0e0e;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        box-shadow: 0 6px 32px rgba(0,0,0,.7);
        font-family: -apple-system, 'Segoe UI', sans-serif;
      }
      #__pins-list-panel .pins-list-header {
        padding: 10px 14px 8px;
        font-size: 11px;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: .1em;
        text-transform: uppercase;
        color: #c080e0;
        border-bottom: 1px solid #1d1d1d;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      #__pins-list-panel .pins-list-header button {
        background: none; border: none; color: #666; cursor: pointer; font-size: 14px;
      }
      #__pins-list-panel .pins-list-header button:hover { color: #ccc; }
      .pins-list-item {
        padding: 9px 14px;
        border-bottom: 1px solid #161616;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .pins-list-item:last-child { border-bottom: none; }
      .pins-list-item-meta {
        font-size: 10px;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        color: #e080b0;
        letter-spacing: .05em;
      }
      .pins-list-item-note {
        font-size: 12px;
        color: #ccc;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .pins-list-item-note:empty::before { content: '(no note)'; color: #444; font-style: italic; }
      .pins-list-item-actions {
        display: flex;
        gap: 5px;
        margin-top: 2px;
      }
      .pins-list-item-actions button {
        font-size: 9px;
        padding: 2px 8px;
        border-radius: 3px;
        border: 1px solid #2d2d2d;
        background: #181818;
        color: #888;
        cursor: pointer;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        letter-spacing: .06em;
        text-transform: uppercase;
        transition: background .1s, color .1s;
      }
      .pins-list-item-actions .pins-resolve-btn:hover { background: #0a2a0a; border-color: #40a040; color: #80d880; }
      .pins-list-item-actions .pins-delete-btn:hover  { background: #2a0a0a; border-color: #a04040; color: #d88080; }
      .pins-list-empty {
        padding: 20px 14px;
        font-size: 12px;
        color: #444;
        font-style: italic;
        text-align: center;
      }
    `;
    document.head.appendChild(style);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Toolbar
  // ─────────────────────────────────────────────────────────────────────────
  const toolbar = document.createElement("div");
  toolbar.id = "__pins-toolbar";
  toolbar.innerHTML = `
    <button id="__pins-btn-pin" title="Toggle pick mode (P)">📌 Pin</button>
    <button id="__pins-btn-list" title="Show all open pins (L)">◉ List</button>
    <button id="__pins-btn-close" title="Deactivate pins overlay">✕ Close</button>
  `;
  document.body.appendChild(toolbar);

  const btnPin   = document.getElementById("__pins-btn-pin");
  const btnList  = document.getElementById("__pins-btn-list");
  const btnClose = document.getElementById("__pins-btn-close");

  // ─────────────────────────────────────────────────────────────────────────
  // Utilities
  // ─────────────────────────────────────────────────────────────────────────
  function isOnToolbar(el) {
    return toolbar.contains(el) ||
      (openPopup && openPopup.contains(el)) ||
      (openMenu  && openMenu.contains(el));
  }

  function closeAllMenus() {
    if (openMenu)  { openMenu.remove();  openMenu  = null; }
    if (openPopup) { openPopup.remove(); openPopup = null; }
  }

  function clampToViewport(el, preferX, preferY) {
    el.style.left = "0px";
    el.style.top  = "0px";
    document.body.appendChild(el);
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth, vh = window.innerHeight;
    const x = Math.min(preferX, vw - rect.width  - 8);
    const y = Math.min(preferY, vh - rect.height - 8);
    el.style.left = Math.max(8, x) + "px";
    el.style.top  = Math.max(8, y) + "px";
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Badge positioning
  // ─────────────────────────────────────────────────────────────────────────
  function positionBadgeOnEntity(badge, entity, entityRef) {
    // entity is a string ref → find the DOM element
    const target = document.querySelector(
      `[data-pin-entity="${CSS.escape(entity)}"][data-pin-id="${CSS.escape(entityRef)}"]`
    );
    if (target) {
      // Position absolutely in document flow — use a wrapper if parent isn't positioned
      const pr = target.getBoundingClientRect();
      const scrollX = window.scrollX, scrollY = window.scrollY;
      badge.style.position = "fixed";
      badge.style.left = (pr.left + 2) + "px";
      badge.style.top  = (pr.top  + 2) + "px";
      // Recompute on scroll/resize
      return target;
    }
    return null;
  }

  function positionBadgeOnRegion(badge, rect) {
    badge.style.position = "fixed";
    badge.style.left = (rect.x + 2) + "px";
    badge.style.top  = (rect.y + 2) + "px";
  }

  function renderBadge(pin, index) {
    if (badgeMap.has(pin.id)) return badgeMap.get(pin.id);

    const badge = document.createElement("div");
    badge.className = "pins-badge";
    badge.textContent = String(index + 1);
    badge.dataset.pinId = pin.id;
    document.body.appendChild(badge);
    badgeMap.set(pin.id, badge);

    // Positioning
    if (pin.entity === "region" && typeof pin.entityRef === "object") {
      positionBadgeOnRegion(badge, pin.entityRef);
    } else if (typeof pin.entityRef === "string") {
      const target = positionBadgeOnEntity(badge, pin.entity, pin.entityRef);
      // If entity moved (scroll/resize), recompute
      if (target) {
        const obs = new ResizeObserver(() => positionBadgeOnEntity(badge, pin.entity, pin.entityRef));
        obs.observe(document.body);
        badge.__obs = obs;
      } else {
        // Fallback: center of viewport
        badge.style.left = "50%";
        badge.style.top  = "50%";
      }
    }

    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      closeAllMenus();
      openBadgeMenu(badge, pin);
    });

    return badge;
  }

  function removeBadge(id) {
    const badge = badgeMap.get(id);
    if (badge) {
      if (badge.__obs) badge.__obs.disconnect();
      badge.remove();
      badgeMap.delete(id);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Badge context menu
  // ─────────────────────────────────────────────────────────────────────────
  function openBadgeMenu(badge, pin) {
    const menu = document.createElement("div");
    menu.className = "pins-badge-menu";
    menu.innerHTML = `
      <div class="pins-note-text">${escapeHtml(pin.note || "")}</div>
      <div class="pins-menu-actions">
        <button class="pins-edit-btn">Edit note</button>
        <button class="pins-resolve-btn">Resolve</button>
        <button class="pins-delete-btn">Delete</button>
      </div>
    `;

    const br = badge.getBoundingClientRect();
    clampToViewport(menu, br.right + 6, br.top);
    openMenu = menu;

    menu.querySelector(".pins-edit-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      closeAllMenus();
      openNotePopup(pin, badge, (savedNote) => {
        pin.note = savedNote;
      });
    });

    menu.querySelector(".pins-resolve-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      closeAllMenus();
      await patchPin(pin.id, { status: "resolved" });
      const b = badgeMap.get(pin.id);
      if (b) {
        b.classList.add("resolved");
        setTimeout(() => removeBadge(pin.id), 300);
      }
    });

    menu.querySelector(".pins-delete-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      closeAllMenus();
      await deletePin(pin.id);
      removeBadge(pin.id);
    });

    // Close when clicking outside
    setTimeout(() => {
      document.addEventListener("click", closeAllMenus, { once: true });
    }, 0);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Note popup
  // ─────────────────────────────────────────────────────────────────────────
  function openNotePopup(pin, anchorEl, onSave) {
    closeAllMenus();

    const popup = document.createElement("div");
    popup.className = "pins-note-popup";
    popup.innerHTML = `
      <textarea class="pins-note-ta" placeholder="Add a note…">${escapeHtml(pin.note || "")}</textarea>
      <div class="pins-popup-hint">Ctrl+Enter save · Esc skip</div>
      <div class="pins-popup-actions">
        <button class="pins-save-btn">Save</button>
        <button class="pins-skip-btn">Skip</button>
      </div>
    `;

    const br = anchorEl ? anchorEl.getBoundingClientRect() : { left: window.innerWidth / 2, top: window.innerHeight / 2, right: window.innerWidth / 2 };
    clampToViewport(popup, br.right + 10, br.top);
    openPopup = popup;

    const ta = popup.querySelector(".pins-note-ta");
    ta.focus();

    async function doSave() {
      const note = ta.value.trim();
      await patchPin(pin.id, { note });
      pin.note = note;
      if (onSave) onSave(note);
      closeAllMenus();
    }

    function doSkip() {
      closeAllMenus();
    }

    popup.querySelector(".pins-save-btn").addEventListener("click", (e) => { e.stopPropagation(); doSave(); });
    popup.querySelector(".pins-skip-btn").addEventListener("click", (e) => { e.stopPropagation(); doSkip(); });

    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); doSave(); }
      if (e.key === "Escape") { e.preventDefault(); doSkip(); }
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Pick mode
  // ─────────────────────────────────────────────────────────────────────────
  function setPickMode(on) {
    pickMode = on;
    btnPin.classList.toggle("__pins-active", on);
    document.body.classList.toggle("__pins-pick-mode", on);
    if (!on) {
      clearHoverState();
      if (hoverLabel) { hoverLabel.remove(); hoverLabel = null; }
    }
  }

  function clearHoverState() {
    if (hoverTarget) {
      hoverTarget.classList.remove("__pins-target-hover");
      hoverTarget = null;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Hover label
  // ─────────────────────────────────────────────────────────────────────────
  function getOrCreateHoverLabel() {
    if (!hoverLabel) {
      hoverLabel = document.createElement("div");
      hoverLabel.id = "__pins-hover-label";
      document.body.appendChild(hoverLabel);
    }
    return hoverLabel;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Mousemove handler (pick mode)
  // ─────────────────────────────────────────────────────────────────────────
  function onMousemove(e) {
    if (!pickMode) return;
    if (isOnToolbar(e.target)) {
      clearHoverState();
      if (hoverLabel) hoverLabel.style.display = "none";
      return;
    }

    const entityEl = e.target.closest("[data-pin-entity]");
    const label = getOrCreateHoverLabel();
    label.style.display = "block";
    label.style.left = (e.clientX + 14) + "px";
    label.style.top  = (e.clientY + 10) + "px";

    if (entityEl) {
      if (entityEl !== hoverTarget) {
        clearHoverState();
        hoverTarget = entityEl;
        entityEl.classList.add("__pins-target-hover");
      }
      const ent = entityEl.dataset.pinEntity;
      const ref = entityEl.dataset.pinRef || entityEl.dataset.pinId || "?";
      label.textContent = `${ent}: ${ref}`;
    } else {
      clearHoverState();
      label.textContent = "region (drag to mark)";
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Click handler (pick mode)
  // ─────────────────────────────────────────────────────────────────────────
  async function onDocumentClick(e) {
    if (!pickMode) return;
    if (isOnToolbar(e.target)) return;
    // Ignore clicks on existing badges
    if (e.target.closest(".pins-badge")) return;

    e.preventDefault();
    e.stopPropagation();

    const entityEl = e.target.closest("[data-pin-entity]");
    let body;

    if (entityEl) {
      const entity    = entityEl.dataset.pinEntity;
      const entityRef = entityEl.dataset.pinRef || entityEl.dataset.pinId || "";
      body = { route: location.pathname, entity, entityRef, note: "" };
    } else {
      // Region fallback
      const x = e.clientX, y = e.clientY;
      body = {
        route: location.pathname,
        entity: "region",
        entityRef: { x, y, w: 40, h: 40 },
        note: "",
      };
    }

    const pin = await postPin(body);
    if (!pin) return;

    const allBadges = Array.from(badgeMap.values());
    const badge = renderBadge(pin, allBadges.length);

    // Exit pick mode after placing
    setPickMode(false);

    // Open note popup anchored to badge
    openNotePopup(pin, badge, null);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // List panel
  // ─────────────────────────────────────────────────────────────────────────
  let listPanel = null;
  let listVisible = false;

  async function toggleList() {
    if (listVisible) {
      closeListPanel();
      return;
    }
    listVisible = true;
    btnList.classList.add("__pins-active");

    if (!listPanel) {
      listPanel = document.createElement("div");
      listPanel.id = "__pins-list-panel";
      document.body.appendChild(listPanel);
    }
    await refreshListPanel();
  }

  function closeListPanel() {
    listVisible = false;
    btnList.classList.remove("__pins-active");
    if (listPanel) { listPanel.remove(); listPanel = null; }
  }

  async function refreshListPanel() {
    if (!listPanel) return;
    const allPins = await fetchPins();
    const open = allPins.filter(p => p.route === location.pathname && p.status === "open");

    listPanel.innerHTML = `
      <div class="pins-list-header">
        <span>pins · ${open.length}</span>
        <button id="__pins-list-close">✕</button>
      </div>
      ${open.length === 0
        ? `<div class="pins-list-empty">No open pins on this route.</div>`
        : open.map((p, i) => `
          <div class="pins-list-item" data-pin-id="${escapeAttr(p.id)}">
            <div class="pins-list-item-meta">#${i + 1} · ${escapeHtml(p.entity)}${typeof p.entityRef === "string" ? `: ${escapeHtml(p.entityRef)}` : " (region)"}</div>
            <div class="pins-list-item-note">${escapeHtml(p.note || "")}</div>
            <div class="pins-list-item-actions">
              <button class="pins-resolve-btn" data-id="${escapeAttr(p.id)}">Resolve</button>
              <button class="pins-delete-btn"  data-id="${escapeAttr(p.id)}">Delete</button>
            </div>
          </div>
        `).join("")
      }
    `;

    listPanel.querySelector("#__pins-list-close")?.addEventListener("click", closeListPanel);

    listPanel.querySelectorAll(".pins-resolve-btn[data-id]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        await patchPin(id, { status: "resolved" });
        const b = badgeMap.get(id);
        if (b) { b.classList.add("resolved"); setTimeout(() => removeBadge(id), 300); }
        await refreshListPanel();
      });
    });

    listPanel.querySelectorAll(".pins-delete-btn[data-id]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        await deletePin(id);
        removeBadge(id);
        await refreshListPanel();
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // API calls
  // ─────────────────────────────────────────────────────────────────────────
  async function fetchPins() {
    try {
      const res = await fetch("/api/pins");
      if (!res.ok) return [];
      const data = await res.json();
      return data.pins || [];
    } catch { return []; }
  }

  async function postPin(body) {
    try {
      const res = await fetch("/api/pins", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.pin || null;
    } catch { return null; }
  }

  async function patchPin(id, patch) {
    try {
      const res = await fetch(`/api/pins/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.pin || null;
    } catch { return null; }
  }

  async function deletePin(id) {
    try {
      await fetch(`/api/pins/${id}`, { method: "DELETE" });
    } catch { /* ignore */ }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Initial load — render existing open pins for this route
  // ─────────────────────────────────────────────────────────────────────────
  async function loadExistingPins() {
    const all = await fetchPins();
    const open = all.filter(p => p.route === location.pathname && p.status === "open");
    open.forEach((pin, i) => renderBadge(pin, i));
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Keyboard shortcuts
  // ─────────────────────────────────────────────────────────────────────────
  function onKeydown(e) {
    // Don't intercept if typing in an input
    if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;

    if (e.key === "p" || e.key === "P") {
      setPickMode(!pickMode);
      return;
    }
    if (e.key === "x" || e.key === "X") {
      if (pickMode) setPickMode(false);
      return;
    }
    if (e.key === "Escape") {
      if (openPopup || openMenu) { closeAllMenus(); return; }
      if (pickMode) { setPickMode(false); return; }
      if (listVisible) { closeListPanel(); return; }
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Button wiring
  // ─────────────────────────────────────────────────────────────────────────
  btnPin.addEventListener("click",   () => setPickMode(!pickMode));
  btnList.addEventListener("click",  toggleList);
  btnClose.addEventListener("click", () => window.__pins.destroy());

  // ─────────────────────────────────────────────────────────────────────────
  // Attach global listeners
  // ─────────────────────────────────────────────────────────────────────────
  document.addEventListener("mousemove", onMousemove);
  document.addEventListener("click",     onDocumentClick, true); // capture phase
  document.addEventListener("keydown",   onKeydown);

  // ─────────────────────────────────────────────────────────────────────────
  // Public API
  // ─────────────────────────────────────────────────────────────────────────
  window.__pins = {
    getPins: fetchPins,

    clearUI() {
      badgeMap.forEach((badge) => {
        if (badge.__obs) badge.__obs.disconnect();
        badge.remove();
      });
      badgeMap.clear();
      closeAllMenus();
      closeListPanel();
      if (hoverLabel) { hoverLabel.remove(); hoverLabel = null; }
      clearHoverState();
    },

    destroy() {
      this.clearUI();
      document.removeEventListener("mousemove", onMousemove);
      document.removeEventListener("click",     onDocumentClick, true);
      document.removeEventListener("keydown",   onKeydown);
      setPickMode(false);
      document.body.classList.remove("__pins-pick-mode");
      toolbar.remove();
      const styleEl = document.getElementById(STYLE_ID);
      if (styleEl) styleEl.remove();
      window.__pins = null;
    },
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────────────────────
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(str) {
    return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Boot
  // ─────────────────────────────────────────────────────────────────────────
  loadExistingPins();

})();
