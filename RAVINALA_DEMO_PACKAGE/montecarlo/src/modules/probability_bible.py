"""
Probability Bible — full interactive encyclopaedia page for RAVINALA.

Entry point: render_probability_bible()
"""
from __future__ import annotations

import html as html_module
import streamlit as st
import streamlit.components.v1 as components

from probability_content import PROBABILITY_BIBLE
from probability_search import (
    search_entries,
    highlight,
    count_by_chapter,
    count_total,
    get_entry_by_id,
)

# ── Design tokens ─────────────────────────────────────────────────────────────
_BG      = "#0A0A0F"
_BG_S    = "#0D0D15"
_BG_CARD = "#13131E"
_ACCENT  = "#00D9A6"
_BLUE    = "#3B82F6"
_AMBER   = "#F59E0B"
_RED     = "#EF4444"
_VIOLET  = "#8B5CF6"
_CYAN    = "#06B6D4"
_ROSE    = "#F43F5E"
_BORDER  = "rgba(255,255,255,0.055)"
_TEXT    = "#E2E8F0"
_MUTED   = "#6B7280"

# ── Entry type → (label, bg_color, text_color) ───────────────────────────────
ENTRY_STYLES: dict[str, tuple[str, str, str]] = {
    "DEFINITION":  ("DEF",    "rgba(59,130,246,0.10)",  "#60A5FA"),
    "THEOREM":     ("THM",    "rgba(0,217,166,0.10)",   "#00D9A6"),
    "LEMMA":       ("LEM",    "rgba(245,158,11,0.10)",  "#FBB830"),
    "PROPOSITION": ("PROP",   "rgba(139,92,246,0.10)",  "#A78BFA"),
    "COROLLARY":   ("COR",    "rgba(6,182,212,0.10)",   "#22D3EE"),
    "EXAMPLE":     ("EX",     "rgba(255,255,255,0.06)", "#94A3B8"),
    "FORMULA":     ("FML",    "rgba(0,217,166,0.06)",   "#00D9A6"),
    "APPLICATION": ("APP",    "rgba(244,63,94,0.10)",   "#FB7185"),
}

LEVEL_COLORS: dict[str, str] = {
    "L1": "#34D399", "L2": "#6EE7B7", "L3": "#A7F3D0",
    "M1": "#60A5FA", "M2": "#3B82F6",
    "PhD": "#A78BFA", "RESEARCH": "#F472B6",
}

ALL_TYPES   = list(ENTRY_STYLES.keys())
ALL_LEVELS  = ["L1", "L2", "L3", "M1", "M2", "PhD", "RESEARCH"]

# ── KaTeX HTML template ───────────────────────────────────────────────────────
_KATEX_HEAD = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{
    delimiters:[
      {left:'$$',right:'$$',display:true},
      {left:'$',right:'$',display:false}
    ],throwOnError:false
  });"></script>
"""

_PAGE_CSS = """
<style>
body { margin:0; padding:0; background:transparent; font-family:'Inter',sans-serif; }

/* ── Nav ────────────────────────────────────────────────────────────── */
.pb-nav { display:flex; flex-direction:column; gap:2px; }
.pb-ch-header {
  display:flex; align-items:center; gap:8px; padding:8px 10px;
  border-radius:8px; cursor:pointer; font-size:0.8rem; font-weight:600;
  color:#94A3B8; letter-spacing:.04em; transition:all .18s ease;
  user-select:none;
}
.pb-ch-header:hover { background:rgba(255,255,255,.04); color:#E2E8F0; }
.pb-ch-header.active { color:#00D9A6; background:rgba(0,217,166,.07); }
.pb-ch-badge {
  margin-left:auto; font-size:.65rem; font-family:'JetBrains Mono',monospace;
  color:#6B7280; background:rgba(255,255,255,.06); padding:1px 6px;
  border-radius:10px;
}
.pb-sec-item {
  padding:5px 12px 5px 26px; font-size:.78rem; color:#6B7280;
  cursor:pointer; border-radius:6px; transition:all .15s ease;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.pb-sec-item:hover { color:#E2E8F0; background:rgba(255,255,255,.03); }
.pb-sec-item.active { color:#00D9A6; background:rgba(0,217,166,.05); }

/* ── Entry cards ─────────────────────────────────────────────────────── */
.pb-card {
  border-radius:12px; padding:20px 22px; margin-bottom:14px;
  border:1px solid rgba(255,255,255,0.055);
  background:rgba(255,255,255,0.018);
  transition:border-color .2s ease;
}
.pb-card:hover { border-color:rgba(0,217,166,0.18); }

.pb-card-header { display:flex; align-items:center; gap:8px; margin-bottom:14px; flex-wrap:wrap; }

.pb-tag {
  display:inline-flex; align-items:center; padding:3px 9px;
  border-radius:6px; font-size:.68rem; font-weight:700;
  letter-spacing:.06em;
}
.pb-level-tag {
  display:inline-flex; align-items:center; padding:2px 8px;
  border-radius:10px; font-size:.65rem; font-weight:600;
  letter-spacing:.05em; border-width:1px; border-style:solid;
}
.pb-card-id {
  margin-left:auto; font-size:.65rem; font-family:'JetBrains Mono',monospace;
  color:#4B5563;
}
.pb-card-title {
  font-size:1.05rem; font-weight:700; color:#E2E8F0; margin-bottom:12px;
  line-height:1.3;
}
.pb-statement {
  font-size:.875rem; color:#CBD5E1; line-height:1.65;
  border-left:2px solid rgba(0,217,166,0.35); padding-left:14px;
  margin-bottom:14px;
}
.pb-formula-block {
  background:rgba(0,0,0,0.3); border-radius:8px; padding:14px 18px;
  margin:12px 0; overflow-x:auto; text-align:center;
  border:1px solid rgba(255,255,255,0.06);
}
.pb-intuition-block {
  background:rgba(0,217,166,0.04); border-radius:8px;
  padding:12px 16px; margin:12px 0; font-size:.85rem;
  color:#94A3B8; line-height:1.6;
  border-left:3px solid rgba(0,217,166,0.3);
}
.pb-intuition-label {
  font-size:.65rem; text-transform:uppercase; letter-spacing:.09em;
  color:#00D9A6; font-weight:700; margin-bottom:5px;
}

/* ── Collapsible sections ────────────────────────────────────────────── */
.pb-collapse-btn {
  display:flex; align-items:center; gap:6px; cursor:pointer;
  padding:7px 0; font-size:.78rem; color:#6B7280;
  background:none; border:none; width:100%; text-align:left;
  transition:color .15s;
}
.pb-collapse-btn:hover { color:#E2E8F0; }
.pb-collapse-btn svg { transition:transform .22s ease; flex-shrink:0; }
.pb-collapse-btn.open svg { transform:rotate(90deg); }
.pb-collapse-body {
  max-height:0; overflow:hidden;
  transition:max-height .35s cubic-bezier(0.4,0,0.2,1);
}
.pb-collapse-body.open { max-height:2000px; }
.pb-collapse-inner {
  background:rgba(0,0,0,0.2); border-radius:8px;
  padding:12px 16px; margin-bottom:10px;
  font-size:.84rem; color:#94A3B8; line-height:1.7;
  border:1px solid rgba(255,255,255,0.04);
}

/* ── Related section ─────────────────────────────────────────────────── */
.pb-related { display:flex; flex-wrap:wrap; gap:6px; margin-top:12px; }
.pb-related-chip {
  font-size:.72rem; padding:3px 10px; border-radius:12px;
  background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
  color:#6B7280; font-family:'JetBrains Mono',monospace;
  cursor:pointer; transition:all .15s;
}
.pb-related-chip:hover { border-color:rgba(0,217,166,0.3); color:#00D9A6; }

/* ── Section headers ─────────────────────────────────────────────────── */
.pb-section-title {
  font-size:1.2rem; font-weight:700; color:#E2E8F0;
  margin:32px 0 18px;
  display:flex; align-items:center; gap:10px;
}
.pb-section-title::before {
  content:''; display:block; width:3px; height:20px;
  background:#00D9A6; border-radius:2px;
}
.pb-chapter-title {
  font-size:1.5rem; font-weight:800; color:#E2E8F0;
  margin:0 0 6px; letter-spacing:-.01em;
}
.pb-chapter-subtitle {
  font-size:.85rem; color:#6B7280; margin-bottom:24px;
}

/* ── Progress badge ──────────────────────────────────────────────────── */
.pb-progress-wrap {
  background:rgba(255,255,255,0.04); border-radius:8px;
  padding:12px 16px; margin-bottom:20px;
}
.pb-progress-bar-bg {
  height:4px; background:rgba(255,255,255,0.08);
  border-radius:2px; overflow:hidden; margin-top:8px;
}
.pb-progress-bar-fill {
  height:100%; border-radius:2px;
  background:linear-gradient(90deg,#00D9A6,#3B82F6);
  transition:width .4s ease;
}

/* ── Search results count ────────────────────────────────────────────── */
.pb-results-count {
  font-size:.78rem; color:#6B7280; margin-bottom:16px;
}
.pb-results-count b { color:#00D9A6; }

/* Responsive */
@media(max-width:640px){ .pb-card { padding:14px 14px; } }
</style>
"""

_COLLAPSE_JS = """
<script>
function pbToggle(id) {
  const btn = document.getElementById('btn_' + id);
  const body = document.getElementById('body_' + id);
  if (!btn || !body) return;
  const open = body.classList.toggle('open');
  btn.classList.toggle('open', open);
}
</script>
"""

_CHEVRON_SVG = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="9 18 15 12 9 6"/></svg>'
)

_INFO_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'
    '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
)

_PROOF_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
)

_EXAMPLE_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/>'
    '<line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
)

_FINANCE_SVG = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="12" y1="1" x2="12" y2="23"/>'
    '<path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>'
)


# ── Card HTML builder ─────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    """HTML-escape a string."""
    return html_module.escape(str(s))


def _collapsible(uid: str, label: str, icon_svg: str, content_html: str) -> str:
    return f"""
<div>
  <button class="pb-collapse-btn" id="btn_{uid}" onclick="pbToggle('{uid}')">
    {icon_svg}&nbsp;{label}{_CHEVRON_SVG}
  </button>
  <div class="pb-collapse-body" id="body_{uid}">
    <div class="pb-collapse-inner">{content_html}</div>
  </div>
</div>"""


def _entry_card(entry: dict, query: str = "", idx: int = 0) -> str:
    etype = entry.get("type", "DEFINITION")
    style = ENTRY_STYLES.get(etype, ENTRY_STYLES["DEFINITION"])
    tag_label, tag_bg, tag_color = style

    level = entry.get("level", "L1")
    lcolor = LEVEL_COLORS.get(level, "#6B7280")
    uid_base = entry["id"].replace(".", "_") + f"_{idx}"

    # Header
    header = f"""
<div class="pb-card-header">
  <span class="pb-tag" style="background:{tag_bg};color:{tag_color}">{tag_label}</span>
  <span class="pb-level-tag" style="color:{lcolor};border-color:{lcolor}33">{level}</span>
  <span class="pb-card-id">#{entry['id']}</span>
</div>"""

    # Title
    title_txt = _esc(entry.get("title", ""))
    if query:
        title_txt = highlight(title_txt, query)
    title_html = f'<div class="pb-card-title">{title_txt}</div>'

    # Statement
    stmt = _esc(entry.get("statement", ""))
    if query:
        stmt = highlight(stmt, query)
    statement_html = f'<div class="pb-statement">{stmt}</div>'

    # Formula
    formula_html = ""
    fl = entry.get("formula_latex")
    if fl:
        formula_html = (
            f'<div class="pb-formula-block">$$\\displaystyle {fl}$$</div>'
        )

    # Intuition
    intuition_html = ""
    intu = entry.get("intuition")
    if intu:
        intuition_html = f"""
<div class="pb-intuition-block">
  <div class="pb-intuition-label">Intuition</div>
  {_esc(intu)}
</div>"""

    # Collapsible: proof
    proof_html = ""
    proof = entry.get("proof")
    if proof:
        proof_body = f"<p>{_esc(proof)}</p>"
        proof_html = _collapsible(
            f"proof_{uid_base}", "Proof / Démonstration", _PROOF_SVG, proof_body
        )

    # Collapsible: example
    example_html = ""
    example = entry.get("example")
    if example:
        ex_body = f"<p>{_esc(example)}</p>"
        example_html = _collapsible(
            f"ex_{uid_base}", "Example", _EXAMPLE_SVG, ex_body
        )

    # Collapsible: finance
    finance_html = ""
    fin = entry.get("finance_application")
    if fin:
        fin_body = f"<p>{_esc(fin)}</p>"
        finance_html = _collapsible(
            f"fin_{uid_base}", "Finance Application", _FINANCE_SVG, fin_body
        )

    # Related
    related_html = ""
    related = entry.get("related", [])
    if related:
        chips = "".join(
            f'<span class="pb-related-chip">→ {_esc(r)}</span>' for r in related
        )
        related_html = f'<div class="pb-related">{chips}</div>'

    card_bg = ENTRY_STYLES.get(etype, ENTRY_STYLES["DEFINITION"])[1]
    return f"""
<div class="pb-card" style="background:{card_bg}">
  {header}
  {title_html}
  {statement_html}
  {formula_html}
  {intuition_html}
  {proof_html}
  {example_html}
  {finance_html}
  {related_html}
</div>"""


def _build_section_html(section: dict, query: str = "") -> str:
    title_html = f'<div class="pb-section-title">{_esc(section["title"])}</div>'
    cards = "".join(
        _entry_card(e, query, i)
        for i, e in enumerate(section.get("entries", []))
    )
    return title_html + cards


def _render_html_block(inner_html: str, height: int = 600) -> None:
    """Render a block of HTML cards with KaTeX support."""
    full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{_KATEX_HEAD}
{_PAGE_CSS}
</head>
<body>
{_COLLAPSE_JS}
{inner_html}
</body>
</html>"""
    components.html(full, height=height, scrolling=True)


# ── Session state helpers ─────────────────────────────────────────────────────

def _ss(key: str, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _get_progress(bible: dict) -> tuple[int, int]:
    mastered = st.session_state.get("pb_mastered", set())
    total = count_total(bible)
    return len(mastered), total


def _toggle_mastered(entry_id: str):
    if "pb_mastered" not in st.session_state:
        st.session_state["pb_mastered"] = set()
    s = st.session_state["pb_mastered"]
    if entry_id in s:
        s.discard(entry_id)
    else:
        s.add(entry_id)


# ── Left navigation column ────────────────────────────────────────────────────

def _render_nav(bible: dict, current_ch: str, current_sec: str) -> None:
    counts = count_by_chapter(bible)
    total = count_total(bible)
    mastered, _ = _get_progress(bible)

    # Progress
    pct = mastered / total * 100 if total else 0
    st.markdown(f"""
<div class="pb-progress-wrap" style="background:rgba(255,255,255,0.04);border-radius:8px;padding:12px 14px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;font-size:.75rem">
    <span style="color:#6B7280">Progress</span>
    <span style="color:#00D9A6;font-family:'JetBrains Mono',monospace">{mastered}/{total}</span>
  </div>
  <div style="height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;margin-top:7px">
    <div style="width:{pct:.1f}%;height:100%;background:linear-gradient(90deg,#00D9A6,#3B82F6);border-radius:2px;transition:width .4s ease"></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Chapter buttons
    for ch in bible.get("chapters", []):
        ch_count = counts.get(ch["id"], 0)
        is_active = ch["id"] == current_ch
        btn_color = "#00D9A6" if is_active else "#94A3B8"
        bg_color = "rgba(0,217,166,0.07)" if is_active else "transparent"

        if st.button(
            f"{ch['id']}. {ch['title']}  ({ch_count})",
            key=f"pb_ch_{ch['id']}",
            width="stretch",
        ):
            st.session_state["pb_chapter"] = ch["id"]
            st.session_state["pb_section"] = None
            st.session_state["pb_search"] = ""
            st.rerun()

        # Expand sections if current chapter
        if is_active:
            for sec in ch.get("sections", []):
                n = len(sec.get("entries", []))
                is_sec_active = sec["id"] == current_sec
                if st.button(
                    f"  {sec['id']} {sec['title']} ({n})",
                    key=f"pb_sec_{sec['id']}",
                    width="stretch",
                ):
                    st.session_state["pb_section"] = sec["id"]
                    st.session_state["pb_search"] = ""
                    st.rerun()


# ── Main content area ─────────────────────────────────────────────────────────

def _render_content(
    bible: dict,
    chapter_id: str,
    section_id: str | None,
    query: str,
    active_levels: list[str],
    active_types: list[str],
) -> None:
    # Find current chapter
    chapter = next(
        (ch for ch in bible["chapters"] if ch["id"] == chapter_id), None
    )
    if not chapter:
        st.warning("Chapter not found.")
        return

    # Search mode: if query or filters are active, show filtered results
    is_filtered = bool(query) or len(active_levels) < len(ALL_LEVELS) or len(active_types) < len(ALL_TYPES)

    if is_filtered:
        results = search_entries(
            bible, query,
            levels=active_levels if len(active_levels) < len(ALL_LEVELS) else None,
            types=active_types if len(active_types) < len(ALL_TYPES) else None,
            chapter_id=chapter_id if not query else None,
        )
        st.markdown(
            f'<div class="pb-results-count">Found <b>{len(results)}</b> entries'
            + (f' matching "<b>{html_module.escape(query)}</b>"' if query else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        if not results:
            st.info("No entries match your current filters.")
            return

        # Render results in batches of 20 (performance)
        page = st.session_state.get("pb_result_page", 0)
        per_page = 20
        total_pages = (len(results) + per_page - 1) // per_page
        batch = results[page * per_page: (page + 1) * per_page]

        # Build HTML for batch
        cards_html = ""
        for i, e in enumerate(batch):
            cards_html += f"""
<div style="font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
            color:#4B5563;margin-bottom:4px">
  {html_module.escape(e['chapter_title'])} › {html_module.escape(e['section_title'])}
</div>"""
            cards_html += _entry_card(e, query, i)

        # Estimate height
        h = min(max(len(batch) * 220, 400), 3200)
        _render_html_block(cards_html, height=h)

        # Pagination
        if total_pages > 1:
            pcols = st.columns(3)
            with pcols[0]:
                if page > 0 and st.button("← Previous", key="pb_prev"):
                    st.session_state["pb_result_page"] = page - 1
                    st.rerun()
            with pcols[1]:
                st.markdown(
                    f'<div style="text-align:center;color:#6B7280;font-size:.8rem;'
                    f'padding-top:6px">Page {page+1}/{total_pages}</div>',
                    unsafe_allow_html=True,
                )
            with pcols[2]:
                if page < total_pages - 1 and st.button("Next →", key="pb_next"):
                    st.session_state["pb_result_page"] = page + 1
                    st.rerun()
        return

    # Normal browse mode
    st.markdown(
        f'<div class="pb-chapter-title">{_esc(chapter["title"])}</div>'
        f'<div class="pb-chapter-subtitle">{_esc(chapter.get("subtitle",""))}</div>',
        unsafe_allow_html=True,
    )

    # Determine which sections to show
    if section_id:
        sections = [s for s in chapter["sections"] if s["id"] == section_id]
    else:
        sections = chapter["sections"]

    for section in sections:
        entries = section.get("entries", [])
        if not entries:
            continue

        st.markdown(
            f'<div class="pb-section-title">{_esc(section["title"])}'
            f'<span style="font-size:.75rem;font-weight:400;color:#6B7280;margin-left:8px">'
            f'{len(entries)} entries</span></div>',
            unsafe_allow_html=True,
        )

        # Progress checkboxes + cards
        for entry in entries:
            mastered = st.session_state.get("pb_mastered", set())
            is_done = entry["id"] in mastered

            # Card in HTML component
            h = _estimate_card_height(entry)
            _render_html_block(_entry_card(entry, "", 0), height=h)

            # Mastered checkbox (native Streamlit — outside HTML component)
            col1, col2 = st.columns([5, 1])
            with col2:
                if st.checkbox(
                    "Mastered",
                    value=is_done,
                    key=f"pb_done_{entry['id']}",
                    label_visibility="collapsed",
                ):
                    if "pb_mastered" not in st.session_state:
                        st.session_state["pb_mastered"] = set()
                    st.session_state["pb_mastered"].add(entry["id"])
                else:
                    if "pb_mastered" in st.session_state:
                        st.session_state["pb_mastered"].discard(entry["id"])


def _estimate_card_height(entry: dict) -> int:
    """Rough height estimate for an entry card iframe."""
    base = 200
    if entry.get("formula_latex"):
        base += 80
    if entry.get("intuition"):
        base += 70
    if entry.get("proof"):
        base += 30
    if entry.get("example"):
        base += 30
    if entry.get("finance_application"):
        base += 30
    if entry.get("related"):
        base += 30
    return min(base, 600)


# ── Main page ─────────────────────────────────────────────────────────────────

def render_probability_bible() -> None:
    """Main entry point — call this from app.py."""
    # Session state init
    _ss("pb_chapter", "1")
    _ss("pb_section", None)
    _ss("pb_search", "")
    _ss("pb_mastered", set())
    _ss("pb_result_page", 0)
    _ss("pb_active_levels", ALL_LEVELS[:])
    _ss("pb_active_types", ALL_TYPES[:])

    bible = PROBABILITY_BIBLE
    total = count_total(bible)

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:24px">
  <h2 style="font-size:1.65rem;font-weight:800;color:#E2E8F0;margin-bottom:4px;letter-spacing:-.01em">
    <span style="color:#00D9A6">◈</span> Probability Bible
  </h2>
  <p style="font-size:.85rem;color:#6B7280;margin:0">
    Interactive encyclopaedia — from L1 foundations to PhD research &nbsp;·&nbsp;
    <span style="color:#00D9A6;font-family:'JetBrains Mono',monospace">{total}</span> entries
  </p>
</div>
""", unsafe_allow_html=True)

    # ── Search + filters row ─────────────────────────────────────────────────
    scol1, scol2 = st.columns([3, 2])
    with scol1:
        q = st.text_input(
            "search",
            value=st.session_state["pb_search"],
            placeholder="Search definitions, theorems, formulas…",
            label_visibility="collapsed",
            key="pb_search_input",
        )
        if q != st.session_state["pb_search"]:
            st.session_state["pb_search"] = q
            st.session_state["pb_result_page"] = 0
            st.rerun()

    with scol2:
        filter_tab1, filter_tab2 = st.tabs(["Level", "Type"])
        with filter_tab1:
            sel_levels = st.multiselect(
                "Levels",
                ALL_LEVELS,
                default=st.session_state["pb_active_levels"],
                key="pb_level_filter",
                label_visibility="collapsed",
            )
            if set(sel_levels) != set(st.session_state["pb_active_levels"]):
                st.session_state["pb_active_levels"] = sel_levels or ALL_LEVELS[:]
                st.session_state["pb_result_page"] = 0
                st.rerun()
        with filter_tab2:
            sel_types = st.multiselect(
                "Types",
                ALL_TYPES,
                default=st.session_state["pb_active_types"],
                key="pb_type_filter",
                label_visibility="collapsed",
            )
            if set(sel_types) != set(st.session_state["pb_active_types"]):
                st.session_state["pb_active_types"] = sel_types or ALL_TYPES[:]
                st.session_state["pb_result_page"] = 0
                st.rerun()

    st.markdown("---")

    # ── Two-column layout: nav | content ─────────────────────────────────────
    nav_col, content_col = st.columns([1, 3], gap="medium")

    with nav_col:
        _render_nav(
            bible,
            st.session_state["pb_chapter"],
            st.session_state["pb_section"],
        )

    with content_col:
        _render_content(
            bible,
            chapter_id=st.session_state["pb_chapter"],
            section_id=st.session_state["pb_section"],
            query=st.session_state["pb_search"],
            active_levels=st.session_state["pb_active_levels"],
            active_types=st.session_state["pb_active_types"],
        )
