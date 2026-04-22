/*
 * Cowork Mark Mode — injectable overlay for marking page regions/elements during a web-cowork session.
 * Claude reads marks via window.__markMode.getMarks() or window.__marks.
 */
(() => {
  if (window.__markMode) { window.__markMode.destroy(); }
  const NS = 'mm';
  const state = { mode: 'off', marks: [], nextId: 1, hoverEl: null, dragStart: null };
  window.__marks = state.marks;

  const style = document.createElement('style');
  style.id = NS + '-style';
  style.textContent = `
    .${NS}-widget { position: fixed; top: 16px; right: 16px; background: rgba(20,24,32,0.96); color: #e6edf3; border: 1px solid #30363d; border-radius: 12px; padding: 10px 12px; font: 12px/1.4 -apple-system,Segoe UI,sans-serif; z-index: 2147483647; box-shadow: 0 10px 24px rgba(0,0,0,0.5); min-width: 200px; backdrop-filter: blur(10px); }
    .${NS}-widget h4 { margin: 0 0 8px; font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: #9aa3ad; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }
    .${NS}-widget .cnt { background: #ec4899; color: white; padding: 1px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; letter-spacing: 0; }
    .${NS}-widget .row { display: flex; gap: 4px; align-items: center; margin: 4px 0; }
    .${NS}-widget button { background: #1f2937; color: #e6edf3; border: 1px solid #374151; border-radius: 6px; padding: 5px 9px; font: inherit; cursor: pointer; flex: 1; transition: all 0.15s; }
    .${NS}-widget button:hover { background: #374151; }
    .${NS}-widget button.active { background: linear-gradient(135deg,#6366f1,#8b5cf6); border-color: transparent; color: white; }
    .${NS}-widget .actions { margin-top: 6px; padding-top: 6px; border-top: 1px solid #30363d; }
    .${NS}-widget .actions button { font-size: 11px; }
    .${NS}-hover { outline: 2px dashed #6366f1 !important; outline-offset: 2px !important; cursor: crosshair !important; }
    .${NS}-mark-el { outline: 2px solid #ec4899 !important; outline-offset: 2px !important; }
    .${NS}-badge { position: absolute; background: linear-gradient(135deg,#ec4899,#f43f5e); color: white; font: 700 11px -apple-system,sans-serif; padding: 2px 7px; border-radius: 999px; z-index: 2147483646; pointer-events: none; box-shadow: 0 3px 8px rgba(236,72,153,0.5); min-width: 18px; text-align: center; }
    .${NS}-rect { position: absolute; border: 2px solid #ec4899; background: rgba(236,72,153,0.12); z-index: 2147483645; pointer-events: none; border-radius: 4px; }
    .${NS}-ghost { position: fixed; border: 2px dashed #6366f1; background: rgba(99,102,241,0.1); z-index: 2147483644; pointer-events: none; border-radius: 4px; }
    .${NS}-note { position: fixed; background: rgba(20,24,32,0.98); color: #e6edf3; border: 1px solid #6366f1; border-radius: 10px; padding: 12px; z-index: 2147483647; min-width: 300px; box-shadow: 0 15px 40px rgba(0,0,0,0.6); }
    .${NS}-note .title { margin-bottom: 8px; font-weight: 600; font-size: 13px; color: #e6edf3; display: flex; align-items: center; gap: 8px; }
    .${NS}-note .title .chip { background: #ec4899; color: white; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .${NS}-note textarea { width: 100%; box-sizing: border-box; background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px 10px; resize: vertical; min-height: 72px; font: 12px/1.4 -apple-system,sans-serif; outline: none; }
    .${NS}-note textarea:focus { border-color: #6366f1; }
    .${NS}-note .footer { margin-top: 8px; display: flex; gap: 6px; justify-content: space-between; align-items: center; }
    .${NS}-note .hint { font-size: 10px; color: #8b93a0; }
    .${NS}-note .btns { display: flex; gap: 6px; }
    .${NS}-note .btn { background: #1f2937; color: #e6edf3; border: 1px solid #374151; border-radius: 6px; padding: 5px 12px; cursor: pointer; font: 11px -apple-system,sans-serif; }
    .${NS}-note .btn.primary { background: linear-gradient(135deg,#6366f1,#8b5cf6); border-color: transparent; color: white; }
  `;
  document.head.appendChild(style);

  const widget = document.createElement('div');
  widget.className = NS + '-widget';
  widget.id = NS + '-widget';
  widget.innerHTML = `
    <h4><span>Mark Mode</span><span class="cnt" id="${NS}-count">0</span></h4>
    <div class="row">
      <button data-mode="element">Element</button>
      <button data-mode="rect">Rect</button>
      <button data-mode="off" class="active">Off</button>
    </div>
    <div class="row actions">
      <button id="${NS}-list">List</button>
      <button id="${NS}-clear">Clear</button>
      <button id="${NS}-close">Close</button>
    </div>
  `;
  document.body.appendChild(widget);

  widget.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
  widget.querySelector('#' + NS + '-clear').addEventListener('click', clearAll);
  widget.querySelector('#' + NS + '-close').addEventListener('click', destroy);
  widget.querySelector('#' + NS + '-list').addEventListener('click', () => {
    const txt = state.marks.length ? state.marks.map(m => `#${m.id} [${m.type}] ${m.note || '(no note)'}`).join('\n') : 'No marks yet';
    alert(txt);
  });

  function setMode(m) {
    state.mode = m;
    widget.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === m));
    document.body.style.cursor = m === 'rect' ? 'crosshair' : '';
    if (state.hoverEl) { state.hoverEl.classList.remove(NS + '-hover'); state.hoverEl = null; }
  }
  function updateCount() { widget.querySelector('#' + NS + '-count').textContent = state.marks.length; }
  function cssPath(el) {
    if (!(el instanceof Element)) return '';
    const path = [];
    while (el && el.nodeType === 1 && path.length < 6) {
      let sel = el.nodeName.toLowerCase();
      if (el.id) { sel = '#' + el.id; path.unshift(sel); break; }
      let sib = el, nth = 1;
      while ((sib = sib.previousElementSibling)) if (sib.nodeName === el.nodeName) nth++;
      sel += `:nth-of-type(${nth})`;
      path.unshift(sel);
      el = el.parentElement;
    }
    return path.join(' > ');
  }
  function inUI(e) { return e.target.closest('.' + NS + '-widget') || e.target.closest('.' + NS + '-note'); }

  function onMove(e) {
    if (state.mode !== 'element' || inUI(e)) return;
    if (state.hoverEl && state.hoverEl !== e.target) state.hoverEl.classList.remove(NS + '-hover');
    state.hoverEl = e.target;
    if (!state.hoverEl.classList.contains(NS + '-mark-el')) state.hoverEl.classList.add(NS + '-hover');
  }
  function onClick(e) {
    if (state.mode !== 'element' || inUI(e)) return;
    e.preventDefault(); e.stopPropagation();
    const el = e.target;
    el.classList.remove(NS + '-hover');
    addElementMark(el);
  }
  function addElementMark(el) {
    const id = state.nextId++;
    el.classList.add(NS + '-mark-el');
    el.setAttribute('data-' + NS + '-id', id);
    const r = el.getBoundingClientRect();
    const badge = document.createElement('div');
    badge.className = NS + '-badge';
    badge.textContent = id;
    badge.style.top = (r.top + window.scrollY - 10) + 'px';
    badge.style.left = (r.left + window.scrollX - 10) + 'px';
    badge.setAttribute('data-' + NS + '-for', id);
    document.body.appendChild(badge);
    const mark = {
      id, type: 'element', tag: el.tagName.toLowerCase(), selector: cssPath(el),
      text: (el.textContent || '').trim().slice(0, 160),
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      note: '', createdAt: new Date().toISOString(),
    };
    state.marks.push(mark); updateCount(); promptNote(mark);
  }

  let ghost = null;
  function onDown(e) {
    if (state.mode !== 'rect' || inUI(e)) return;
    e.preventDefault();
    state.dragStart = { x: e.clientX, y: e.clientY };
    ghost = document.createElement('div');
    ghost.className = NS + '-ghost';
    document.body.appendChild(ghost);
  }
  function onMoveRect(e) {
    if (!state.dragStart || !ghost) return;
    const x1 = state.dragStart.x, y1 = state.dragStart.y, x2 = e.clientX, y2 = e.clientY;
    ghost.style.left = Math.min(x1, x2) + 'px';
    ghost.style.top = Math.min(y1, y2) + 'px';
    ghost.style.width = Math.abs(x2 - x1) + 'px';
    ghost.style.height = Math.abs(y2 - y1) + 'px';
  }
  function onUp(e) {
    if (!state.dragStart || !ghost) return;
    const x1 = state.dragStart.x, y1 = state.dragStart.y, x2 = e.clientX, y2 = e.clientY;
    const rect = { x: Math.min(x1, x2) + window.scrollX, y: Math.min(y1, y2) + window.scrollY, w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) };
    ghost.remove(); ghost = null; state.dragStart = null;
    if (rect.w < 6 || rect.h < 6) return;
    addRectMark(rect);
  }
  function addRectMark(rect) {
    const id = state.nextId++;
    const div = document.createElement('div');
    div.className = NS + '-rect';
    div.style.left = rect.x + 'px'; div.style.top = rect.y + 'px';
    div.style.width = rect.w + 'px'; div.style.height = rect.h + 'px';
    div.setAttribute('data-' + NS + '-id', id);
    document.body.appendChild(div);
    const badge = document.createElement('div');
    badge.className = NS + '-badge';
    badge.textContent = id;
    badge.style.top = (rect.y - 10) + 'px';
    badge.style.left = (rect.x - 10) + 'px';
    badge.setAttribute('data-' + NS + '-for', id);
    document.body.appendChild(badge);
    const mark = { id, type: 'rect', rect, note: '', createdAt: new Date().toISOString() };
    state.marks.push(mark); updateCount(); promptNote(mark);
  }

  function promptNote(mark) {
    const note = document.createElement('div');
    note.className = NS + '-note';
    const desc = mark.type === 'element' ? (mark.tag + ' · ' + (mark.text.slice(0, 40) || 'no text')) : 'Region mark';
    note.innerHTML = `
      <div class="title"><span class="chip">#${mark.id}</span><span></span></div>
      <textarea placeholder="What should Claude do here? (edit, fix, explain…)"></textarea>
      <div class="footer">
        <span class="hint">Ctrl+Enter save · Esc skip</span>
        <div class="btns">
          <button class="btn" data-act="skip">Skip</button>
          <button class="btn primary" data-act="save">Save</button>
        </div>
      </div>`;
    note.querySelector('.title span:last-child').textContent = desc;
    note.style.top = '130px'; note.style.right = '16px';
    document.body.appendChild(note);
    const ta = note.querySelector('textarea');
    setTimeout(() => ta.focus(), 10);
    const close = (save) => { if (save) mark.note = ta.value.trim(); note.remove(); };
    note.querySelector('[data-act="save"]').addEventListener('click', () => close(true));
    note.querySelector('[data-act="skip"]').addEventListener('click', () => close(false));
    ta.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.stopPropagation(); close(false); }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); close(true); }
    });
  }

  function clearAll() {
    document.querySelectorAll('.' + NS + '-mark-el').forEach(el => { el.classList.remove(NS + '-mark-el'); el.removeAttribute('data-' + NS + '-id'); });
    document.querySelectorAll('.' + NS + '-badge, .' + NS + '-rect').forEach(el => el.remove());
    state.marks.length = 0; state.nextId = 1; updateCount();
  }
  function destroy() {
    clearAll();
    document.removeEventListener('mousemove', onMove, true);
    document.removeEventListener('click', onClick, true);
    document.removeEventListener('mousedown', onDown, true);
    document.removeEventListener('mousemove', onMoveRect, true);
    document.removeEventListener('mouseup', onUp, true);
    document.removeEventListener('keydown', onKey, true);
    widget.remove(); style.remove();
    document.body.style.cursor = '';
    delete window.__markMode; delete window.__marks;
  }
  function onKey(e) {
    if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') return;
    if (e.key === 'Escape' && state.mode !== 'off') { setMode('off'); return; }
    if (e.key === 'e' || e.key === 'E') setMode('element');
    else if (e.key === 'r' || e.key === 'R') setMode('rect');
    else if (e.key === 'x' || e.key === 'X') setMode('off');
  }

  document.addEventListener('mousemove', onMove, true);
  document.addEventListener('click', onClick, true);
  document.addEventListener('mousedown', onDown, true);
  document.addEventListener('mousemove', onMoveRect, true);
  document.addEventListener('mouseup', onUp, true);
  document.addEventListener('keydown', onKey, true);

  window.__markMode = { setMode, clearAll, destroy, getMarks: () => JSON.parse(JSON.stringify(state.marks)) };
  console.log('[cowork] mark-mode ready — window.__markMode');
})();
